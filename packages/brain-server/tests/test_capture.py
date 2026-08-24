"""Tests for plugins/brain/scripts/capture.py.

The SessionEnd hook: gate on whether the session was meaningful, run a headless
`claude -p` (Sonnet) extractor over the transcript, dedupe candidates, and
`brain write` each one to the inbox. It runs async and must never raise.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import load_script


@pytest.fixture
def mod():
    return load_script("capture")


# ---- dedupe ----------------------------------------------------------------


def test_dedupe_by_normalized_title(mod):
    cands = [
        {"title": "Prefers uv", "type": "preference", "body": "x"},
        {"title": "prefers   uv", "type": "preference", "body": "y"},  # dup (case/space)
        {"title": "Other thing", "type": "fact", "body": "z"},
    ]
    out = mod.dedupe_candidates(cands)
    assert [c["title"] for c in out] == ["Prefers uv", "Other thing"]


def test_dedupe_drops_empty_titles(mod):
    assert mod.dedupe_candidates([{"title": "  ", "body": "x"}, {"body": "y"}]) == []


# ---- meaningful-session gate -----------------------------------------------


def _records(n_user: int, chars: int):
    body = "a" * chars
    recs = []
    for i in range(n_user):
        recs.append({"type": "user", "message": {"role": "user", "content": body}})
        recs.append({"type": "assistant", "message": {"role": "assistant", "content": "ok"}})
    return recs


def test_meaningful_requires_turns_and_volume(mod):
    assert mod.is_meaningful_session(_records(1, 50)) is False   # too thin
    assert mod.is_meaningful_session([]) is False
    assert mod.is_meaningful_session(_records(3, 600)) is True   # enough back-and-forth


# ---- extractor output parsing ----------------------------------------------


def test_parse_extractor_plain_array(mod):
    raw = json.dumps({"result": json.dumps([{"title": "T", "type": "fact", "body": "b"}])})
    out = mod.parse_extractor_output(raw)
    assert out[0]["title"] == "T"


def test_parse_extractor_fenced_json(mod):
    inner = "```json\n[{\"title\": \"T\", \"type\": \"fact\", \"body\": \"b\"}]\n```"
    raw = json.dumps({"result": inner})
    assert mod.parse_extractor_output(raw)[0]["title"] == "T"


def test_parse_extractor_empty_array(mod):
    assert mod.parse_extractor_output(json.dumps({"result": "[]"})) == []


def test_parse_extractor_garbage_is_empty(mod):
    assert mod.parse_extractor_output("not json") == []
    assert mod.parse_extractor_output(json.dumps({"result": "sorry, nothing to save"})) == []


# ---- brain write command ---------------------------------------------------


def test_brain_write_cmd_shape(mod):
    cmd = mod.brain_write_cmd(
        {"title": "T", "type": "preference", "body": "b", "confidence": 0.6,
         "tags": ["python"], "links": ["uv"]},
        session_id="sess1",
    )
    assert "write" in cmd
    assert "--title" in cmd and "T" in cmd
    assert "--type" in cmd and "preference" in cmd
    assert "--tier" in cmd and "inbox" in cmd
    assert "--source-session" in cmd and "sess1" in cmd
    assert "--confidence" in cmd and "0.6" in cmd
    assert "--body-file" in cmd and "-" in cmd  # body comes via stdin


# ---- main flow -------------------------------------------------------------


def test_main_noop_when_session_not_meaningful(mod, monkeypatch, tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
    extractor_calls = {"n": 0}
    monkeypatch.setattr(mod, "run_extractor", lambda text: extractor_calls.__setitem__("n", 1) or [])
    mod.main(stdin_text=json.dumps({"transcript_path": str(transcript), "session_id": "s"}))
    assert extractor_calls["n"] == 0  # gated out before the expensive call


def test_main_writes_each_candidate(mod, monkeypatch, tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(
        json.dumps(r) for r in _records(3, 600)
    ) + "\n")
    monkeypatch.setattr(mod, "run_extractor", lambda text: [
        {"title": "A", "type": "fact", "body": "ba"},
        {"title": "a", "type": "fact", "body": "dup"},  # deduped away
        {"title": "B", "type": "preference", "body": "bb"},
    ])
    writes = []
    monkeypatch.setattr(mod, "write_candidate", lambda c, sid: writes.append(c["title"]))
    mod.main(stdin_text=json.dumps({"transcript_path": str(transcript), "session_id": "s"}))
    assert writes == ["A", "B"]


def test_main_never_raises_on_bad_input(mod):
    mod.main(stdin_text="not json")  # must not raise
    mod.main(stdin_text=json.dumps({"transcript_path": "/no/such/file", "session_id": "s"}))
