from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from brain_server.api import create_app

AUTH = {"Authorization": "Bearer testtoken"}


@pytest.fixture
def client(cfg):
    # `with` triggers lifespan startup/shutdown (writer + index init).
    with TestClient(create_app(cfg)) as c:
        yield c


def test_healthz_no_auth(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_recall_requires_auth(client):
    assert client.get("/recall", params={"q": "uv"}).status_code == 401


def test_write_recall_get_roundtrip(client):
    r = client.post(
        "/notes",
        headers=AUTH,
        json={"title": "Prefers uv", "type": "preference", "body": "uses uv for packaging",
              "tags": ["python"], "confidence": 0.8},
    )
    assert r.status_code == 200
    nid = r.json()["id"]

    hits = client.get("/recall", headers=AUTH, params={"q": "uv packaging"}).json()["hits"]
    assert nid in [h["id"] for h in hits]

    note = client.get(f"/notes/{nid}", headers=AUTH).json()
    assert note["frontmatter"]["title"] == "Prefers uv"
    # recall + this get each bumped access at least twice
    assert note["frontmatter"]["access_count"] >= 1


def test_review_flow(client):
    nid = client.post(
        "/notes", headers=AUTH,
        json={"title": "Inbox item", "type": "fact", "body": "a fact about uv"},
    ).json()["id"]

    q = client.get("/review/queue", headers=AUTH, params={"since": "7d"}).json()["items"]
    assert nid in [i["id"] for i in q]

    assert client.post("/review/promote", headers=AUTH, json={"id": nid}).json()["ok"]
    note = client.get(f"/notes/{nid}", headers=AUTH).json()
    assert note["frontmatter"]["tier"] == "longterm"
    assert note["frontmatter"]["review"] == "elevated"


def test_stats(client):
    client.post("/notes", headers=AUTH, json={"title": "x", "type": "fact", "body": "y"})
    s = client.get("/stats", headers=AUTH).json()
    assert s["total"] >= 1


def test_rebuild_reconciles_index_with_vault(client, cfg):
    """POST /admin/rebuild repopulates the index from the vault on disk.

    Drop a note file directly into the vault (as a sync/Obsidian edit would),
    bypassing the API, then rebuild and confirm it becomes recallable.
    """
    from brain_server.repository import note_path, write_note

    from tests.test_repository import _make_note

    note = _make_note(title="Dropped in by sync", body="rebuild target zzz")
    write_note(cfg.vault, note)  # not via the API → index doesn't know yet
    assert note.frontmatter.id not in [
        h["id"] for h in client.get("/recall", headers=AUTH, params={"q": "zzz"}).json()["hits"]
    ]

    r = client.post("/admin/rebuild", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["notes"] >= 1

    hits = client.get("/recall", headers=AUTH, params={"q": "zzz"}).json()["hits"]
    assert note.frontmatter.id in [h["id"] for h in hits]
    assert note_path(cfg.vault, "inbox", note.frontmatter.id).exists()


def test_rebuild_requires_auth(client):
    assert client.post("/admin/rebuild").status_code == 401


def test_link_and_neighbors(client):
    a = client.post("/notes", headers=AUTH,
                    json={"title": "A", "type": "fact", "body": "node a"}).json()["id"]
    b = client.post("/notes", headers=AUTH,
                    json={"title": "B", "type": "fact", "body": "node b"}).json()["id"]
    assert client.post("/links", headers=AUTH, json={"src": a, "dst": b}).json()["ok"]
    res = client.get(f"/notes/{a}/neighbors", headers=AUTH, params={"depth": 1}).json()
    assert b in [e["dst"] for e in res["edges"]]
    assert b in [n["id"] for n in res["nodes"]]


def test_discard_moves_to_archive(client):
    nid = client.post("/notes", headers=AUTH,
                      json={"title": "junk", "type": "fact", "body": "discard me"}).json()["id"]
    assert client.post("/review/discard", headers=AUTH, json={"id": nid}).json()["ok"]
    fm = client.get(f"/notes/{nid}", headers=AUTH).json()["frontmatter"]
    assert fm["tier"] == "archived"
    assert fm["review"] == "discarded"


def test_merge_marks_sources_merged(client):
    a = client.post("/notes", headers=AUTH,
                    json={"title": "dup A", "type": "fact", "body": "merge a"}).json()["id"]
    keep = client.post("/notes", headers=AUTH,
                       json={"title": "keep", "type": "fact", "body": "merge keep"}).json()["id"]
    assert client.post("/review/merge", headers=AUTH, json={"ids": [a], "into": keep}).json()["ok"]
    fm_a = client.get(f"/notes/{a}", headers=AUTH).json()["frontmatter"]
    assert fm_a["status"] == "merged"
    assert fm_a["merged_into"] == keep
    assert fm_a["tier"] == "archived"
    # the kept note is untouched
    assert client.get(f"/notes/{keep}", headers=AUTH).json()["frontmatter"]["status"] == "active"


def test_merge_skips_self_and_missing(client):
    keep = client.post("/notes", headers=AUTH,
                       json={"title": "keep", "type": "fact", "body": "k"}).json()["id"]
    # ids include the target itself and a non-existent id; both are skipped silently
    r = client.post("/review/merge", headers=AUTH,
                    json={"ids": [keep, "01MISSING"], "into": keep})
    assert r.json()["ok"]
    assert client.get(f"/notes/{keep}", headers=AUTH).json()["frontmatter"]["status"] == "active"


def test_get_missing_returns_404(client):
    assert client.get("/notes/01DOESNOTEXIST", headers=AUTH).status_code == 404


def test_promote_missing_returns_404(client):
    r = client.post("/review/promote", headers=AUTH, json={"id": "01DOESNOTEXIST"})
    assert r.status_code == 404


def test_recall_with_filters(client):
    client.post("/notes", headers=AUTH,
                json={"title": "pref note", "type": "preference", "body": "filter target uvx"})
    client.post("/notes", headers=AUTH,
                json={"title": "fact note", "type": "fact", "body": "filter target uvx"})
    hits = client.get("/recall", headers=AUTH,
                      params={"q": "uvx", "type": "preference"}).json()["hits"]
    assert hits and all(h["type"] == "preference" for h in hits)


def test_dev_mode_disables_auth(vault):
    """When no token is configured the server runs open (loopback dev mode)."""
    from brain_server.api import create_app
    from brain_server.config import Config

    cfg = Config(vault=vault, db=vault / ".brain" / "index.db", token="",
                 host="127.0.0.1", port=8765)
    with TestClient(create_app(cfg)) as c:
        assert c.get("/recall", params={"q": "anything"}).status_code == 200


def test_parse_since():
    from datetime import datetime, timezone

    from brain_server.api import parse_since

    now = datetime.now(timezone.utc)

    def age(spec):
        return (now - datetime.strptime(parse_since(spec), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)).total_seconds()

    assert age("1h") < age("7d") < age("2w")
    # garbage falls back to the 7d default (~604800s), not an error
    assert abs(age("garbage") - age("7d")) < 5
