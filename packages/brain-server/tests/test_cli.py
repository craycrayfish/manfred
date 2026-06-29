"""Tests for the `brain` CLI (plugins/brain/bin/brain).

Two layers:
 * unit — load the script as a module via importlib and exercise pure helpers
   (config resolution precedence, offline outbox enqueue/drain ordering);
 * e2e — run the CLI as a subprocess against a real server subprocess, with an
   isolated HOME so the outbox never touches the developer's ~/.brain.
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "plugins" / "brain" / "bin" / "brain"
PKG_DIR = Path(__file__).resolve().parents[1]
TOKEN = "clitoken"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def cli_mod():
    """The bin/brain script loaded as an importable module (no .py extension)."""
    loader = SourceFileLoader("braincli", str(CLI))
    spec = importlib.util.spec_from_loader("braincli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def server(tmp_path):
    """A real brain_server subprocess on a free port with a temp vault."""
    port = _free_port()
    vault = tmp_path / "srv-vault"
    env = {
        **os.environ,
        "BRAIN_VAULT": str(vault),
        "BRAIN_DB": str(vault / ".brain" / "index.db"),
        "BRAIN_TOKEN": TOKEN,
        "BRAIN_HOST": "127.0.0.1",
        "BRAIN_PORT": str(port),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "brain_server"],
        cwd=str(PKG_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(base + "/healthz", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server did not start")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_cli(args, base, home, *, stdin: str | None = None, token: str = TOKEN):
    env = {
        **os.environ,
        "BRAIN_URL": base,
        "BRAIN_TOKEN": token,
        "HOME": str(home),  # isolate ~/.brain/outbox.ndjson
    }
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        env=env, input=stdin, capture_output=True, text=True,
    )


# ---- unit: config resolution ----------------------------------------------


def test_config_env_wins(cli_mod, monkeypatch):
    monkeypatch.setenv("BRAIN_URL", "http://env-host:1/")
    monkeypatch.setenv("BRAIN_TOKEN", "envtoken")
    url, token = cli_mod.resolve_config()
    assert url == "http://env-host:1"  # trailing slash stripped
    assert token == "envtoken"


def test_config_local_file_then_home(cli_mod, monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_URL", raising=False)
    monkeypatch.delenv("BRAIN_TOKEN", raising=False)
    local = tmp_path / "brain.local.json"
    local.write_text(json.dumps({"url": "http://local:2", "token": "lt"}))
    monkeypatch.setattr(cli_mod, "PLUGIN_LOCAL", local)
    monkeypatch.setattr(cli_mod, "HOME_CONFIG", tmp_path / "nope.json")
    assert cli_mod.resolve_config() == ("http://local:2", "lt")


def test_config_default_when_nothing(cli_mod, monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_URL", raising=False)
    monkeypatch.delenv("BRAIN_TOKEN", raising=False)
    monkeypatch.setattr(cli_mod, "PLUGIN_LOCAL", tmp_path / "a.json")
    monkeypatch.setattr(cli_mod, "HOME_CONFIG", tmp_path / "b.json")
    assert cli_mod.resolve_config() == (cli_mod.DEFAULT_URL, "")


# ---- unit: outbox ordering -------------------------------------------------


def test_outbox_drain_preserves_order_on_partial_failure(cli_mod, monkeypatch, tmp_path):
    outbox = tmp_path / "outbox.ndjson"
    monkeypatch.setattr(cli_mod, "OUTBOX", outbox)
    for i in range(3):
        cli_mod._enqueue("/notes", {"title": f"n{i}", "type": "fact", "body": ""})

    calls = []

    def fake_request(method, url, token, payload=None, timeout=5):
        calls.append(payload["title"])
        if payload["title"] == "n1":  # second item fails -> rest must stay queued
            raise cli_mod.Offline()
        return {}

    monkeypatch.setattr(cli_mod, "_request", fake_request)
    sent = cli_mod._drain_outbox("http://x", "t")
    assert sent == 1  # only n0 went
    assert calls == ["n0", "n1"]  # stopped at the failure, didn't try n2
    remaining = [json.loads(ln)["payload"]["title"] for ln in outbox.read_text().splitlines()]
    assert remaining == ["n1", "n2"]  # FIFO order preserved


# ---- e2e: subprocess CLI <-> subprocess server -----------------------------


def test_write_recall_get_e2e(server, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    w = run_cli(["write", "--title", "uv pref", "--type", "preference",
                 "--body-file", "-"], server, home, stdin="loves uv tooling")
    assert w.returncode == 0
    nid = w.stdout.strip()

    r = run_cli(["recall", "uv tooling", "--json"], server, home)
    assert nid in [h["id"] for h in json.loads(r.stdout)["hits"]]

    g = run_cli(["get", nid, "--json"], server, home)
    assert json.loads(g.stdout)["frontmatter"]["title"] == "uv pref"


def test_offline_queue_then_flush_e2e(server, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    # point at a dead port so the write goes to the outbox
    dead = "http://127.0.0.1:1"
    off = run_cli(["write", "--title", "queued", "--type", "fact", "--body", "later"], dead, home)
    assert off.returncode == 0
    assert (home / ".brain" / "outbox.ndjson").exists()

    flush = run_cli(["flush"], server, home)
    assert flush.returncode == 0
    assert "flushed 1" in flush.stdout
    assert not (home / ".brain" / "outbox.ndjson").exists()

    found = run_cli(["recall", "queued later", "--json"], server, home)
    assert json.loads(found.stdout)["hits"]


def test_rebuild_command_e2e(server, tmp_path):
    """`brain rebuild` triggers POST /admin/rebuild and reports the note count."""
    home = tmp_path / "home"
    home.mkdir()
    run_cli(["write", "--title", "a", "--type", "fact", "--body", "x"], server, home)
    out = run_cli(["rebuild", "--json"], server, home)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["ok"] is True
