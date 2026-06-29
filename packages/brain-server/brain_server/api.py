"""FastAPI app: routes, bearer auth, and the BrainStore orchestrator.

BrainStore ties together the repository (vault files), the index (SQLite), and
the single-writer queue. All mutations funnel through ``writer.submit`` so the
vault and index are mutated by exactly one task at a time. Reads hit the index
directly and bump access counters (the decay signal) as a side effect.
"""

from __future__ import annotations

import asyncio
import hmac
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from . import __version__
from .config import Config, load_config
from .index import Index
from .models import (
    DiscardRequest,
    LinkRequest,
    MergeRequest,
    Note,
    NoteFrontmatter,
    PromoteRequest,
    WriteRequest,
)
from .repository import (
    find_note_path,
    move_tier,
    new_id,
    read_note,
    utcnow_iso,
    write_note,
)
from .watcher import watch_vault

_SINCE = re.compile(r"^(\d+)([hdw])$")


def parse_since(spec: str) -> str:
    """Turn ``7d`` / ``24h`` / ``2w`` into an absolute UTC ISO cutoff."""
    m = _SINCE.match(spec.strip())
    if not m:
        m = _SINCE.match("7d")
    n, unit = int(m.group(1)), m.group(2)
    delta = {"h": timedelta(hours=n), "d": timedelta(days=n), "w": timedelta(weeks=n)}[unit]
    cutoff = datetime.now(timezone.utc) - delta
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


class BrainStore:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.index = Index(cfg.db)
        self._writer = None  # type: ignore[assignment]
        self._watch_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        from .writer import Writer

        for tier_dir in ("inbox", "longterm", "archive", ".brain"):
            (self.cfg.vault / tier_dir).mkdir(parents=True, exist_ok=True)
        # Reconcile the index from the vault on boot (handles offline edits).
        self.index.rebuild(self.cfg.vault)
        self._writer = Writer(self._apply)
        self._writer.start()
        self._watch_task = asyncio.create_task(
            watch_vault(self.cfg.vault, self.index, self._stop)
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._writer is not None:
            await self._writer.stop()
        self.index.close()

    # ---- write ops (run inside the single writer) -------------------------

    def _apply(self, op: dict[str, Any]) -> Any:
        kind = op["kind"]
        if kind == "create":
            return self._create(op["req"])
        if kind == "link":
            return self._link(op["req"])
        if kind == "promote":
            return self._move(op["id"], "longterm", review="elevated", status="active")
        if kind == "discard":
            return self._move(op["id"], "archived", review="discarded", status="archived")
        if kind == "merge":
            return self._merge(op["ids"], op["into"])
        raise ValueError(f"unknown op {kind}")

    def _create(self, req: WriteRequest) -> dict:
        now = utcnow_iso()
        fm = NoteFrontmatter(
            id=new_id(),
            title=req.title,
            type=req.type,
            tier=req.tier,
            status="active",
            tags=req.tags,
            created=now,
            created_by=req.created_by,
            source_session=req.source_session,
            last_accessed=now,
            access_count=0,
            confidence=req.confidence,
            review="pending",
            links=req.links,
        )
        note = Note(frontmatter=fm, body=req.body)
        path = write_note(self.cfg.vault, note)
        self.index.upsert(note, str(path))
        return {"id": fm.id}

    def _link(self, req: LinkRequest) -> dict:
        path = find_note_path(self.cfg.vault, req.src)
        if path is not None:
            note = read_note(path)
            if req.dst not in note.frontmatter.links:
                note.frontmatter.links.append(req.dst)
                write_note(self.cfg.vault, note)
                self.index.upsert(note, str(path))
        self.index.add_edge(req.src, req.dst, req.rel)
        return {"ok": True}

    def _move(self, note_id: str, tier: str, *, review: str, status: str) -> dict:
        path = find_note_path(self.cfg.vault, note_id)
        if path is None:
            raise HTTPException(404, f"note {note_id} not found")
        note = read_note(path)
        note.frontmatter.review = review  # type: ignore[assignment]
        note.frontmatter.status = status  # type: ignore[assignment]
        new_path = move_tier(self.cfg.vault, note, tier)
        self.index.upsert(note, str(new_path))
        return {"ok": True}

    def _merge(self, ids: list[str], into: str) -> dict:
        for nid in ids:
            if nid == into:
                continue
            path = find_note_path(self.cfg.vault, nid)
            if path is None:
                continue
            note = read_note(path)
            note.frontmatter.status = "merged"  # type: ignore[assignment]
            note.frontmatter.review = "merged"  # type: ignore[assignment]
            note.frontmatter.merged_into = into
            if into not in note.frontmatter.links:
                note.frontmatter.links.append(into)
            new_path = move_tier(self.cfg.vault, note, "archived")
            self.index.upsert(note, str(new_path))
        return {"ok": True}

    async def submit(self, op: dict[str, Any]) -> Any:
        assert self._writer is not None
        return await self._writer.submit(op)

    # ---- reads (direct, with access bump) ---------------------------------

    def get_note(self, note_id: str) -> dict | None:
        path = find_note_path(self.cfg.vault, note_id)
        if path is None:
            return None
        note = read_note(path)
        self.index.bump_access(note_id)
        fm = note.frontmatter.model_dump()
        # Access telemetry lives in the index (the file isn't rewritten on every
        # read); overlay the authoritative counters onto the returned frontmatter.
        meta = self.index.get_meta(note_id)
        if meta is not None:
            fm["access_count"] = meta["access_count"]
            fm["last_accessed"] = meta["last_accessed"]
        return {"frontmatter": fm, "body": note.body}

    def recall(self, q, type_, tier, k) -> list[dict]:
        hits = self.index.recall(q, type_, tier, k)
        for h in hits:
            self.index.bump_access(h["id"])
        return hits

    def neighbors(self, note_id: str, depth: int) -> dict:
        self.index.bump_access(note_id)
        return self.index.neighbors(note_id, depth)


# ---- auth -----------------------------------------------------------------


def _make_auth(cfg: Config):
    def require_auth(authorization: str = Header(default="")) -> None:
        if not cfg.token:  # dev mode: auth disabled when no token configured
            return
        expected = f"Bearer {cfg.token}"
        if not hmac.compare_digest(authorization, expected):
            raise HTTPException(401, "unauthorized")

    return require_auth


# ---- app factory ----------------------------------------------------------


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = BrainStore(cfg)
        await store.start()
        app.state.store = store
        try:
            yield
        finally:
            await store.stop()

    app = FastAPI(title="brain-server", version=__version__, lifespan=lifespan)
    auth = Depends(_make_auth(cfg))

    def store(app_=app) -> BrainStore:
        return app_.state.store

    @app.get("/healthz")
    async def healthz():
        s: BrainStore = app.state.store
        return {
            "ok": True,
            "notes": s.index.stats()["total"],
            "outbox_hint": "client-side ~/.brain/outbox.ndjson",
            "version": __version__,
        }

    @app.get("/recall", dependencies=[auth])
    async def recall(
        q: str,
        type: str | None = None,
        tier: str | None = None,
        k: int = Query(8, ge=1, le=50),
    ):
        return {"hits": app.state.store.recall(q, type, tier, k)}

    @app.get("/notes/{note_id}", dependencies=[auth])
    async def get_note(note_id: str):
        note = app.state.store.get_note(note_id)
        if note is None:
            raise HTTPException(404, "not found")
        return note

    @app.get("/notes/{note_id}/neighbors", dependencies=[auth])
    async def neighbors(note_id: str, depth: int = Query(1, ge=0, le=3)):
        return app.state.store.neighbors(note_id, depth)

    @app.post("/notes", dependencies=[auth])
    async def create_note(req: WriteRequest):
        return await app.state.store.submit({"kind": "create", "req": req})

    @app.post("/links", dependencies=[auth])
    async def add_link(req: LinkRequest):
        return await app.state.store.submit({"kind": "link", "req": req})

    @app.get("/review/queue", dependencies=[auth])
    async def review_queue(since: str = "7d"):
        return {"items": app.state.store.index.review_queue(parse_since(since))}

    @app.post("/review/promote", dependencies=[auth])
    async def promote(req: PromoteRequest):
        return await app.state.store.submit({"kind": "promote", "id": req.id})

    @app.post("/review/merge", dependencies=[auth])
    async def merge(req: MergeRequest):
        return await app.state.store.submit({"kind": "merge", "ids": req.ids, "into": req.into})

    @app.post("/review/discard", dependencies=[auth])
    async def discard(req: DiscardRequest):
        return await app.state.store.submit({"kind": "discard", "id": req.id})

    @app.get("/stats", dependencies=[auth])
    async def stats():
        return app.state.store.index.stats()

    return app
