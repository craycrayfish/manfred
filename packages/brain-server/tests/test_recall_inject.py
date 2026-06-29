"""Tests for plugins/brain/scripts/recall_inject.py.

The UserPromptSubmit hook: a cheap local gate decides whether the prompt is
memory-relevant; only then does it call `brain recall` and inject hits as an
additionalSystemPrompt. It must never raise (a hook error would break the turn)
and must skip the network entirely when gated out.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import load_script


@pytest.fixture
def mod():
    return load_script("recall_inject")


# ---- gate: skip cases ------------------------------------------------------


@pytest.mark.parametrize("prompt", ["yes", "no", "ok", "okay", "thanks", "thank you",
                                    "go on", "continue", "sure", "yep", "done", "k"])
def test_gate_skips_acknowledgements(mod, prompt):
    assert mod.is_memory_relevant(prompt) is False


def test_gate_skips_trivially_short(mod):
    assert mod.is_memory_relevant("fix it") is False
    assert mod.is_memory_relevant("") is False


def test_gate_skips_command_echo(mod):
    assert mod.is_memory_relevant("/compact") is False
    assert mod.is_memory_relevant("!ls -la /tmp") is False


# ---- gate: trigger cases ---------------------------------------------------


@pytest.mark.parametrize("prompt", [
    "how do I usually set up a python project?",
    "what did I decide about the database schema?",
    "remember my deployment preferences",
    "what's my preferred test framework?",
    "use the same conventions we established for the brain server",
])
def test_gate_triggers_on_memory_signals(mod, prompt):
    assert mod.is_memory_relevant(prompt) is True


# ---- injection formatting --------------------------------------------------


def test_build_injection_empty_is_empty_dict(mod):
    assert mod.build_injection([]) == {}


def test_build_injection_includes_titles_and_ids(mod):
    inj = mod.build_injection([
        {"id": "01A", "type": "preference", "title": "Prefers uv", "snippet": "uses uv"},
        {"id": "01B", "type": "fact", "title": "Mac mini host", "snippet": ""},
    ])
    asp = inj["additionalSystemPrompt"]
    assert "Prefers uv" in asp
    assert "Mac mini host" in asp
    assert "01A" in asp and "01B" in asp


# ---- main: end-to-end with recall stubbed ----------------------------------


def test_main_skips_network_when_gated_out(mod, monkeypatch, capsys):
    called = {"n": 0}
    monkeypatch.setattr(mod, "recall", lambda q: called.__setitem__("n", called["n"] + 1) or [])
    mod.main(stdin_text=json.dumps({"prompt": "yes"}))
    assert json.loads(capsys.readouterr().out) == {}
    assert called["n"] == 0  # never hit the brain


def test_main_injects_when_relevant(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "recall",
                        lambda q: [{"id": "01A", "type": "fact", "title": "T", "snippet": "S"}])
    mod.main(stdin_text=json.dumps({"prompt": "what did I decide about deployment?"}))
    out = json.loads(capsys.readouterr().out)
    assert "T" in out["additionalSystemPrompt"]


def test_main_emits_empty_on_no_hits(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "recall", lambda q: [])
    mod.main(stdin_text=json.dumps({"prompt": "what did I decide about deployment?"}))
    assert json.loads(capsys.readouterr().out) == {}


def test_main_never_raises_on_recall_failure(mod, monkeypatch, capsys):
    def boom(q):
        raise RuntimeError("offline")

    monkeypatch.setattr(mod, "recall", boom)
    mod.main(stdin_text=json.dumps({"prompt": "what did I decide about deployment?"}))
    assert json.loads(capsys.readouterr().out) == {}


def test_main_handles_malformed_stdin(mod, capsys):
    mod.main(stdin_text="not json at all")
    assert json.loads(capsys.readouterr().out) == {}
