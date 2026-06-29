"""Tests for the `manfred` CLI (brain_server.manfred) — server lifecycle wrapper.

Covers the pure logic: dotenv parsing, settings precedence, vault bootstrap,
pid/liveness helpers, server-env construction, and arg dispatch. Process
spawning (up/down) is exercised by an integration smoke test, not here.
"""

from __future__ import annotations

import os


from brain_server import manfred


# ---- dotenv parsing --------------------------------------------------------


def test_load_env_file_parses_and_strips(tmp_path):
    f = tmp_path / "env"
    f.write_text(
        '# a comment\n'
        'BRAIN_TOKEN="abc123"\n'
        "export BRAIN_PORT=9000\n"
        "\n"
        "BRAIN_HOST=1.2.3.4\n"
        "NOT_BRAIN=ignored-but-loaded\n"
    )
    d = manfred.load_env_file(f)
    assert d["BRAIN_TOKEN"] == "abc123"   # quotes stripped
    assert d["BRAIN_PORT"] == "9000"      # `export ` prefix stripped
    assert d["BRAIN_HOST"] == "1.2.3.4"


# ---- settings precedence ---------------------------------------------------


def test_resolve_env_overrides_file(tmp_path):
    f = tmp_path / "env"
    f.write_text("BRAIN_PORT=9000\nBRAIN_VAULT=/tmp/x\nBRAIN_TOKEN=fromfile\n")
    s = manfred.resolve_settings({"BRAIN_PORT": "7000"}, [f])
    assert s["port"] == 7000                  # env wins over file
    assert str(s["vault"]) == "/tmp/x"        # file value used
    assert s["token"] == "fromfile"
    assert s["db"] == s["vault"] / ".brain" / "index.db"  # derived default


def test_resolve_defaults_when_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    s = manfred.resolve_settings({}, [tmp_path / "missing"])
    assert s["host"] == "127.0.0.1"
    assert s["port"] == 8765
    assert s["token"] == ""
    assert s["vault"] == tmp_path / "brain-vault"


def test_resolve_uses_first_existing_file(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    b.write_text("BRAIN_PORT=1111\n")  # only b exists
    s = manfred.resolve_settings({}, [a, b])
    assert s["port"] == 1111


# ---- vault bootstrap -------------------------------------------------------


def test_ensure_vault_copies_template(tmp_path):
    template = tmp_path / "template"
    (template / "inbox").mkdir(parents=True)
    (template / "_meta").mkdir()
    (template / "_meta" / "conventions.md").write_text("# conventions")
    vault = tmp_path / "vault"
    manfred.ensure_vault(vault, template)
    assert (vault / "inbox").is_dir()
    assert (vault / "_meta" / "conventions.md").read_text() == "# conventions"


def test_ensure_vault_mkdir_fallback_without_template(tmp_path):
    vault = tmp_path / "vault"
    manfred.ensure_vault(vault, None)
    for d in ("inbox", "longterm", "archive"):
        assert (vault / d).is_dir()


def test_ensure_vault_noop_when_present(tmp_path):
    vault = tmp_path / "vault"
    (vault / "inbox").mkdir(parents=True)
    sentinel = vault / "inbox" / "keep.md"
    sentinel.write_text("mine")
    manfred.ensure_vault(vault, None)  # must not clobber
    assert sentinel.read_text() == "mine"


# ---- pid / liveness --------------------------------------------------------


def test_pid_alive(tmp_path):
    assert manfred.pid_alive(os.getpid()) is True
    assert manfred.pid_alive(2_000_000_000) is False


def test_running_pid_reads_live_pidfile(tmp_path):
    pf = tmp_path / "server.pid"
    pf.write_text(str(os.getpid()))
    assert manfred.running_pid(pf) == os.getpid()


def test_running_pid_none_for_dead_or_missing(tmp_path):
    assert manfred.running_pid(tmp_path / "missing.pid") is None
    pf = tmp_path / "server.pid"
    pf.write_text("2000000000")  # not a live process
    assert manfred.running_pid(pf) is None


# ---- server env ------------------------------------------------------------


def test_build_server_env_stringifies_settings(tmp_path):
    s = {"vault": tmp_path / "v", "db": tmp_path / "v" / ".brain" / "index.db",
         "host": "127.0.0.1", "port": 8799, "token": "t"}
    env = manfred.build_server_env(s, base={"PATH": "/usr/bin"})
    assert env["PATH"] == "/usr/bin"           # base preserved
    assert env["BRAIN_VAULT"] == str(tmp_path / "v")
    assert env["BRAIN_PORT"] == "8799"         # int -> str
    assert env["BRAIN_TOKEN"] == "t"


def test_build_server_env_omits_empty_token(tmp_path):
    s = {"vault": tmp_path / "v", "db": tmp_path / "v" / "i.db",
         "host": "127.0.0.1", "port": 8765, "token": ""}
    env = manfred.build_server_env(s, base={})
    assert "BRAIN_TOKEN" not in env  # dev mode: no token in the child env


# ---- dispatch --------------------------------------------------------------


def test_main_unknown_command_nonzero(capsys):
    assert manfred.main(["bogus"]) != 0
    assert manfred.main(["brain", "frobnicate"]) != 0


def test_main_help_zero(capsys):
    assert manfred.main(["brain", "help"]) == 0
    out = capsys.readouterr().out
    assert "up" in out and "down" in out


def test_main_routes_to_handler(monkeypatch):
    seen = {}

    def fake_status(settings):
        seen["status"] = True
        return 0

    monkeypatch.setattr(manfred, "cmd_status", fake_status)
    rc = manfred.main(["brain", "status"])
    assert rc == 0
    assert seen.get("status") is True
