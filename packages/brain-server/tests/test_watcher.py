from __future__ import annotations

from watchfiles import Change

from brain_server.repository import note_path, write_note
from brain_server.watcher import reconcile_change
from tests.test_repository import _make_note


def test_reconcile_added_indexes_note(index, vault):
    note = _make_note(title="External add", body="appeared via obsidian zzz")
    path = write_note(vault, note)  # written outside the server
    assert index.recall("zzz") == []
    reconcile_change(index, Change.added, str(path))
    assert note.frontmatter.id in [h["id"] for h in index.recall("zzz")]


def test_reconcile_modified_refreshes_fts(index, vault):
    note = _make_note(title="Edit me", body="original word alpha")
    path = write_note(vault, note)
    reconcile_change(index, Change.added, str(path))
    note.body = "now contains beta"
    write_note(vault, note)
    reconcile_change(index, Change.modified, str(path))
    assert index.recall("beta")
    assert index.recall("alpha") == []


def test_reconcile_deleted_removes_from_index(index, vault):
    note = _make_note(body="deleteme zzz")
    path = write_note(vault, note)
    reconcile_change(index, Change.added, str(path))
    assert index.recall("zzz")
    path.unlink()
    reconcile_change(index, Change.deleted, str(path))
    assert index.recall("zzz") == []
    assert index.get_meta(note.frontmatter.id) is None


def test_reconcile_ignores_non_markdown(index, vault):
    sidecar = vault / "inbox" / "notes.txt"
    sidecar.write_text("not a note")
    reconcile_change(index, Change.added, str(sidecar))  # must not raise
    assert index.stats()["total"] == 0


def test_reconcile_swallows_malformed_note(index, vault):
    bad = note_path(vault, "inbox", "01BADNOTE")
    bad.write_text("---\nnot: valid frontmatter for our schema\n---\nbody")
    reconcile_change(index, Change.added, str(bad))  # must not raise
    assert index.stats()["total"] == 0


def test_reconcile_deleted_stale_path_keeps_moved_note(index, vault):
    # A tier move writes the new-tier file then deletes the old one; the
    # delete event for the stale path must not drop the note from the index.
    note = _make_note(body="promoted zzz")
    old_path = write_note(vault, note)
    reconcile_change(index, Change.added, str(old_path))
    note.frontmatter.tier = "longterm"
    new_path = write_note(vault, note)
    index.upsert(note, str(new_path))
    old_path.unlink()
    reconcile_change(index, Change.deleted, str(old_path))
    assert index.get_meta(note.frontmatter.id) is not None
    assert index.recall("zzz")
