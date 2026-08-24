"""Vault file I/O: markdown <-> frontmatter, atomic writes, tier moves.

The vault is the source of truth. Every mutation goes through here and is made
durable with a temp-file + ``os.replace`` so a crash never leaves a half-written
note. Filenames are ``{id}.md``; the folder is the note's current tier.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import ulid

from .models import Note, NoteFrontmatter

TIERS = ("inbox", "longterm", "archived")
# On disk the "archived" tier lives in an "archive/" folder (shorter, matches
# the vault skeleton); everything else maps 1:1 to its tier name.
_TIER_DIR = {"inbox": "inbox", "longterm": "longterm", "archived": "archive"}


def new_id() -> str:
    """A fresh ULID string (lexicographically sortable, time-prefixed)."""
    return ulid.new().str


def utcnow_iso() -> str:
    """Current UTC time as ``2026-06-28T10:15:00Z``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tier_dir(vault: Path, tier: str) -> Path:
    return vault / _TIER_DIR[tier]


def note_path(vault: Path, tier: str, note_id: str) -> Path:
    return tier_dir(vault, tier) / f"{note_id}.md"


def find_note_path(vault: Path, note_id: str) -> Path | None:
    """Locate a note by id across all tier folders."""
    for tier in TIERS:
        p = note_path(vault, tier, note_id)
        if p.exists():
            return p
    return None


def _serialize(note: Note) -> str:
    post = frontmatter.Post(note.body, **note.frontmatter.model_dump())
    return frontmatter.dumps(post)


def read_note(path: Path) -> Note:
    post = frontmatter.load(str(path))
    fm = NoteFrontmatter.model_validate(post.metadata)
    return Note(frontmatter=fm, body=post.content)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_note(vault: Path, note: Note) -> Path:
    """Write a note to its tier folder atomically; returns the file path."""
    path = note_path(vault, note.frontmatter.tier, note.frontmatter.id)
    _atomic_write(path, _serialize(note))
    return path


def move_tier(vault: Path, note: Note, new_tier: str) -> Path:
    """Move a note to a new tier: update frontmatter, atomically relocate file."""
    old_path = find_note_path(vault, note.frontmatter.id)
    note.frontmatter.tier = new_tier  # type: ignore[assignment]
    new_path = write_note(vault, note)
    if old_path is not None and old_path != new_path and old_path.exists():
        old_path.unlink()
    return new_path
