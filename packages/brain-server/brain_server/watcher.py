"""Filesystem watcher: reconcile the index with direct (Obsidian) vault edits.

When a note file changes outside the server (e.g. the user edits it in Obsidian),
re-read it and upsert; on deletion, drop it from the index. Reconciliation is
best-effort — failures are swallowed so a malformed file never crashes the loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from watchfiles import Change, awatch

from .index import Index
from .repository import read_note


def reconcile_change(index: Index, change: Change, raw: str) -> None:
    """Apply a single filesystem change to the index. Best-effort.

    Non-markdown paths are ignored; a malformed note never raises (so one bad
    file can't kill the watch loop).
    """
    path = Path(raw)
    if path.suffix != ".md":
        return
    note_id = path.stem
    try:
        if change == Change.deleted:
            index.remove(note_id)
        elif path.exists():
            index.upsert(read_note(path), str(path))
    except Exception:  # noqa: BLE001 - never let one bad file kill the watcher
        return


async def watch_vault(vault: Path, index: Index, stop: asyncio.Event) -> None:
    watch_dirs = [str(vault / d) for d in ("inbox", "longterm", "archive") if (vault / d).exists()]
    if not watch_dirs:
        return
    async for changes in awatch(*watch_dirs, stop_event=stop):
        for change, raw in changes:
            reconcile_change(index, change, raw)
