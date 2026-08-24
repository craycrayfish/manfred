from __future__ import annotations

from brain_server.models import Note, NoteFrontmatter
from brain_server.repository import (
    find_note_path,
    move_tier,
    new_id,
    note_path,
    read_note,
    utcnow_iso,
    write_note,
)


def _make_note(**over) -> Note:
    now = utcnow_iso()
    fm = NoteFrontmatter(
        id=over.get("id", new_id()),
        title=over.get("title", "Prefers uv over pip"),
        type=over.get("type", "preference"),
        tier=over.get("tier", "inbox"),
        created=now,
        last_accessed=now,
        tags=over.get("tags", ["python", "tooling"]),
        links=over.get("links", ["python-tooling"]),
    )
    return Note(frontmatter=fm, body=over.get("body", "Shawn reaches for `uv`. See [[python-tooling]]."))


def test_roundtrip(vault):
    note = _make_note()
    path = write_note(vault, note)
    assert path == note_path(vault, "inbox", note.frontmatter.id)
    loaded = read_note(path)
    assert loaded.frontmatter.id == note.frontmatter.id
    assert loaded.frontmatter.title == note.frontmatter.title
    assert loaded.frontmatter.tags == ["python", "tooling"]
    assert "uv" in loaded.body


def test_atomic_write_leaves_no_tmp(vault):
    note = _make_note()
    write_note(vault, note)
    assert not list((vault / "inbox").glob("*.tmp"))


def test_move_tier(vault):
    note = _make_note()
    write_note(vault, note)
    nid = note.frontmatter.id
    new_path = move_tier(vault, note, "longterm")
    assert new_path == note_path(vault, "longterm", nid)
    assert not note_path(vault, "inbox", nid).exists()
    assert find_note_path(vault, nid) == new_path
    assert read_note(new_path).frontmatter.tier == "longterm"
