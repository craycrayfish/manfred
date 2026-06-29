from __future__ import annotations

from brain_server.models import Note, NoteFrontmatter
from brain_server.repository import new_id, utcnow_iso, write_note


def _note(index, vault, title, body, type_="preference", tags=None, links=None):
    now = utcnow_iso()
    fm = NoteFrontmatter(
        id=new_id(),
        title=title,
        type=type_,
        tier="inbox",
        created=now,
        last_accessed=now,
        tags=tags or [],
        links=links or [],
    )
    note = Note(frontmatter=fm, body=body)
    path = write_note(vault, note)
    index.upsert(note, str(path))
    return note


def test_recall_finds_by_keyword(index, vault):
    n = _note(index, vault, "Prefers uv over pip", "Shawn uses uv for python packaging", tags=["python"])
    hits = index.recall("uv packaging")
    ids = [h["id"] for h in hits]
    assert n.frontmatter.id in ids


def test_recall_empty_query(index, vault):
    _note(index, vault, "Anything", "body")
    assert index.recall("   ") == []


def test_recall_type_filter(index, vault):
    _note(index, vault, "Pref one", "uv tooling", type_="preference")
    d = _note(index, vault, "Decision one", "uv tooling decision", type_="decision")
    hits = index.recall("uv", type_="decision")
    assert [h["id"] for h in hits] == [d.frontmatter.id]


def test_access_bump(index, vault):
    n = _note(index, vault, "Bumpable", "content here")
    assert index.get_meta(n.frontmatter.id)["access_count"] == 0
    index.bump_access(n.frontmatter.id)
    index.bump_access(n.frontmatter.id)
    assert index.get_meta(n.frontmatter.id)["access_count"] == 2


def test_edges_from_links_and_wikilinks(index, vault):
    a = _note(index, vault, "Note A", "links to [[note-b]] inline", links=["note-c"])
    res = index.neighbors(a.frontmatter.id, depth=1)
    dsts = {e["dst"] for e in res["edges"]}
    assert {"note-b", "note-c"} <= dsts


def test_rebuild(index, vault):
    n = _note(index, vault, "Rebuildme", "uv content")
    index.rebuild(vault)
    hits = index.recall("uv")
    assert n.frontmatter.id in [h["id"] for h in hits]


def test_upsert_updates_fts(index, vault):
    n = _note(index, vault, "Original title", "original body about pip")
    # mutate body and re-upsert
    n.frontmatter.title = "Updated title"
    write_note(vault, n)
    index.upsert(n, str(vault / "inbox" / f"{n.frontmatter.id}.md"))
    assert n.frontmatter.id in [h["id"] for h in index.recall("Updated")]
