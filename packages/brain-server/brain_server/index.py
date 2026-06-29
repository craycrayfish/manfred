"""Derived SQLite index: FTS recall, edges, access bumps, rebuild.

The index is rebuildable from the vault at any time (``rebuild``); the DB file
is disposable. A single ``threading.Lock`` serializes all SQLite access so the
async server and the watcher never collide on the connection.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from pathlib import Path

from .models import Note
from .repository import TIERS, read_note, tier_dir, utcnow_iso

_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_WORD = re.compile(r"\w+", re.UNICODE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
  id            TEXT PRIMARY KEY,
  path          TEXT NOT NULL,
  title         TEXT NOT NULL,
  type          TEXT NOT NULL,
  tier          TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active',
  tags          TEXT NOT NULL DEFAULT '[]',
  created       TEXT NOT NULL,
  last_accessed TEXT NOT NULL,
  access_count  INTEGER NOT NULL DEFAULT 0,
  confidence    REAL,
  review        TEXT NOT NULL DEFAULT 'pending',
  created_by    TEXT,
  source_session TEXT,
  content_hash  TEXT NOT NULL
);

-- Standard (not contentless) FTS5: lets us DELETE/UPDATE rows by rowid cheaply
-- when a note changes or the watcher reconciles. fts_map ties the integer rowid
-- to the note's ULID. (Deviation from the spec's content='' table, chosen for
-- maintenance simplicity per the locked "optimize for simplicity" goal.)
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
  title, body, tags,
  tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS fts_map (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  id    TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS edges (
  src_id   TEXT NOT NULL,
  dst_id   TEXT NOT NULL,
  rel_type TEXT NOT NULL DEFAULT 'relates_to',
  PRIMARY KEY (src_id, dst_id, rel_type)
);

CREATE INDEX IF NOT EXISTS idx_notes_tier ON notes(tier);
CREATE INDEX IF NOT EXISTS idx_notes_last_accessed ON notes(last_accessed);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_id);
"""


def content_hash(title: str, body: str) -> str:
    return hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest()


def _fts_query(q: str) -> str:
    """Turn a free-text query into a safe FTS5 MATCH expression.

    Tokenize to words, prefix-match each, OR them together. Returns ``""`` when
    the query has no usable tokens (caller should short-circuit to no hits).
    """
    tokens = _WORD.findall(q.lower())
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"*' for t in tokens)


class Index:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- write path -------------------------------------------------------

    def _rowid_for(self, note_id: str) -> int:
        row = self._conn.execute("SELECT rowid FROM fts_map WHERE id=?", (note_id,)).fetchone()
        if row is not None:
            return row["rowid"]
        cur = self._conn.execute("INSERT INTO fts_map(id) VALUES (?)", (note_id,))
        return int(cur.lastrowid)

    def upsert(self, note: Note, path: str) -> None:
        """Insert/replace a note's index row, FTS entry, and edges."""
        fm = note.frontmatter
        ch = content_hash(fm.title, note.body)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO notes (id, path, title, type, tier, status, tags, created,
                    last_accessed, access_count, confidence, review, created_by,
                    source_session, content_hash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    path=excluded.path, title=excluded.title, type=excluded.type,
                    tier=excluded.tier, status=excluded.status, tags=excluded.tags,
                    confidence=excluded.confidence, review=excluded.review,
                    created_by=excluded.created_by, source_session=excluded.source_session,
                    content_hash=excluded.content_hash
                """,
                (
                    fm.id, path, fm.title, fm.type, fm.tier, fm.status,
                    json.dumps(fm.tags), fm.created, fm.last_accessed, fm.access_count,
                    fm.confidence, fm.review, fm.created_by, fm.source_session, ch,
                ),
            )
            rowid = self._rowid_for(fm.id)
            self._conn.execute("DELETE FROM notes_fts WHERE rowid=?", (rowid,))
            self._conn.execute(
                "INSERT INTO notes_fts(rowid, title, body, tags) VALUES (?,?,?,?)",
                (rowid, fm.title, note.body, " ".join(fm.tags)),
            )
            self._replace_edges(fm.id, self._extract_targets(note))
            self._conn.commit()

    def _extract_targets(self, note: Note) -> list[str]:
        targets = list(note.frontmatter.links)
        targets += _WIKILINK.findall(note.body)
        # normalize + dedupe, drop self-links
        seen, out = set(), []
        for t in targets:
            t = t.strip()
            if not t or t == note.frontmatter.id or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out

    def _replace_edges(self, src_id: str, targets: list[str]) -> None:
        self._conn.execute("DELETE FROM edges WHERE src_id=?", (src_id,))
        for dst in targets:
            self._conn.execute(
                "INSERT OR IGNORE INTO edges(src_id, dst_id, rel_type) VALUES (?,?,?)",
                (src_id, dst, "relates_to"),
            )

    def add_edge(self, src: str, dst: str, rel: str = "relates_to") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO edges(src_id, dst_id, rel_type) VALUES (?,?,?)",
                (src, dst, rel),
            )
            self._conn.commit()

    def remove(self, note_id: str) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT rowid FROM fts_map WHERE id=?", (note_id,)
            ).fetchone()
            if row is not None:
                self._conn.execute("DELETE FROM notes_fts WHERE rowid=?", (row["rowid"],))
                self._conn.execute("DELETE FROM fts_map WHERE id=?", (note_id,))
            self._conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
            self._conn.execute("DELETE FROM edges WHERE src_id=? OR dst_id=?", (note_id, note_id))
            self._conn.commit()

    def set_fields(self, note_id: str, **fields) -> None:
        """Patch arbitrary scalar columns on a note row (tier, status, review...)."""
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._lock:
            self._conn.execute(
                f"UPDATE notes SET {cols} WHERE id=?", (*fields.values(), note_id)
            )
            self._conn.commit()

    # ---- read path --------------------------------------------------------

    def bump_access(self, note_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE notes SET last_accessed=?, access_count=access_count+1 WHERE id=?",
                (utcnow_iso(), note_id),
            )
            self._conn.commit()

    def get_meta(self, note_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM notes WHERE id=?", (note_id,)
            ).fetchone()

    def recall(
        self, q: str, type_: str | None = None, tier: str | None = None, k: int = 8
    ) -> list[dict]:
        match = _fts_query(q)
        if not match:
            return []
        clauses = ["notes_fts MATCH ?"]
        params: list = [match]
        if type_:
            clauses.append("n.type=?")
            params.append(type_)
        if tier:
            clauses.append("n.tier=?")
            params.append(tier)
        params.append(k)
        sql = f"""
            SELECT n.id, n.title, n.type, n.tier,
                   snippet(notes_fts, 1, '[', ']', '…', 12) AS snippet,
                   bm25(notes_fts) AS score
            FROM notes_fts
            JOIN fts_map m ON notes_fts.rowid = m.rowid
            JOIN notes n ON n.id = m.id
            WHERE {' AND '.join(clauses)}
            ORDER BY score ASC
            LIMIT ?
        """
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def neighbors(self, note_id: str, depth: int = 1) -> dict:
        """BFS out to ``depth`` over edges (both directions), resolved to notes."""
        with self._lock:
            frontier = {note_id}
            seen = {note_id}
            edges: list[dict] = []
            for _ in range(max(depth, 0)):
                nxt: set[str] = set()
                for nid in frontier:
                    rows = self._conn.execute(
                        "SELECT src_id, dst_id, rel_type FROM edges WHERE src_id=? OR dst_id=?",
                        (nid, nid),
                    ).fetchall()
                    for r in rows:
                        edges.append({"src": r["src_id"], "dst": r["dst_id"], "rel": r["rel_type"]})
                        for other in (r["src_id"], r["dst_id"]):
                            if other not in seen:
                                nxt.add(other)
                seen.update(nxt)
                frontier = nxt
                if not frontier:
                    break
            qmarks = ",".join("?" * len(seen))
            nodes = self._conn.execute(
                f"SELECT id, title, type, tier FROM notes WHERE id IN ({qmarks})",
                tuple(seen),
            ).fetchall()
        # dedupe edges
        uniq = {(e["src"], e["dst"], e["rel"]): e for e in edges}
        return {"nodes": [dict(n) for n in nodes], "edges": list(uniq.values())}

    def review_queue(self, since_iso: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT n.id, n.title, n.type, n.confidence, n.created,
                       snippet(notes_fts, 1, '', '', '…', 16) AS snippet
                FROM notes n
                LEFT JOIN fts_map m ON m.id = n.id
                LEFT JOIN notes_fts ON notes_fts.rowid = m.rowid
                WHERE n.tier='inbox' AND n.review='pending' AND n.created >= ?
                ORDER BY n.created DESC
                """,
                (since_iso,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._lock:
            by_tier = {
                r["tier"]: r["c"]
                for r in self._conn.execute(
                    "SELECT tier, COUNT(*) c FROM notes GROUP BY tier"
                ).fetchall()
            }
            by_type = {
                r["type"]: r["c"]
                for r in self._conn.execute(
                    "SELECT type, COUNT(*) c FROM notes GROUP BY type"
                ).fetchall()
            }
            total = self._conn.execute("SELECT COUNT(*) c FROM notes").fetchone()["c"]
        return {"total": total, "by_tier": by_tier, "by_type": by_type}

    def all_paths(self) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute("SELECT id, path, content_hash FROM notes").fetchall()
        return {r["id"]: r["content_hash"] for r in rows}

    # ---- rebuild ----------------------------------------------------------

    def rebuild(self, vault: Path) -> int:
        """Drop and repopulate the index from the vault. Returns note count."""
        with self._lock:
            self._conn.executescript(
                "DELETE FROM notes; DELETE FROM notes_fts; DELETE FROM fts_map; DELETE FROM edges;"
            )
            self._conn.commit()
        count = 0
        for tier in TIERS:
            d = tier_dir(vault, tier)
            if not d.exists():
                continue
            for md in sorted(d.glob("*.md")):
                try:
                    note = read_note(md)
                except Exception:
                    continue
                self.upsert(note, str(md))
                count += 1
        return count
