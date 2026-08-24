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


def test_recall_handles_special_chars(index, vault):
    # punctuation / FTS operators must not crash the MATCH query
    _note(index, vault, "Weird", "uses AND/OR (parens) and \"quotes\" plus C++")
    assert index.recall('(parens) "quotes" AND') is not None  # no exception
    assert index.recall("!@#$%^&*()") == []  # no word tokens -> no hits


def test_recall_tier_filter(index, vault):
    n = _note(index, vault, "Inbox pref", "tierfilter target")
    n.frontmatter.tier = "longterm"
    index.upsert(n, str(write_note(vault, n)))
    assert index.recall("tierfilter", tier="inbox") == []
    assert n.frontmatter.id in [h["id"] for h in index.recall("tierfilter", tier="longterm")]


def test_recall_unicode(index, vault):
    n = _note(index, vault, "Café résumé 日本語", "naïve emoji 🚀 façade")
    assert n.frontmatter.id in [h["id"] for h in index.recall("façade")]


def test_neighbors_depth(index, vault):
    a = _note(index, vault, "A", "links [[node-b]]", links=[])
    # depth 0 returns just the node, no edges traversed
    res0 = index.neighbors(a.frontmatter.id, depth=0)
    assert res0["edges"] == []
    res1 = index.neighbors(a.frontmatter.id, depth=1)
    assert any(e["dst"] == "node-b" for e in res1["edges"])


def test_review_queue_filters_by_tier_and_time(index, vault):
    inbox = _note(index, vault, "Fresh inbox", "candidate uv")
    items = index.review_queue("2000-01-01T00:00:00Z")
    assert inbox.frontmatter.id in [i["id"] for i in items]
    # future cutoff excludes everything
    assert index.review_queue("2999-01-01T00:00:00Z") == []


def test_stats_groups(index, vault):
    _note(index, vault, "p", "x", type_="preference")
    _note(index, vault, "d", "y", type_="decision")
    s = index.stats()
    assert s["total"] == 2
    assert s["by_type"]["preference"] == 1
    assert s["by_type"]["decision"] == 1
    assert s["by_tier"]["inbox"] == 2


def test_remove_clears_all_tables(index, vault):
    n = _note(index, vault, "Bye", "remove zzz", links=["x"])
    index.remove(n.frontmatter.id)
    assert index.get_meta(n.frontmatter.id) is None
    assert index.recall("zzz") == []
    assert index.neighbors(n.frontmatter.id)["edges"] == []


def test_upsert_updates_fts(index, vault):
    n = _note(index, vault, "Original title", "original body about pip")
    # mutate body and re-upsert
    n.frontmatter.title = "Updated title"
    write_note(vault, n)
    index.upsert(n, str(vault / "inbox" / f"{n.frontmatter.id}.md"))
    assert n.frontmatter.id in [h["id"] for h in index.recall("Updated")]
