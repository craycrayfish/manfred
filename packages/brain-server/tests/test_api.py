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
