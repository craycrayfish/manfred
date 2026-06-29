from __future__ import annotations

from pathlib import Path

from brain_server.config import load_config


def test_defaults(monkeypatch, tmp_path):
    for k in ("BRAIN_VAULT", "BRAIN_DB", "BRAIN_TOKEN", "BRAIN_HOST", "BRAIN_PORT"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config()
    assert cfg.vault == tmp_path / "brain-vault"
    assert cfg.db == tmp_path / "brain-vault" / ".brain" / "index.db"
    assert cfg.token == ""
    assert cfg.host == "127.0.0.1"  # never 0.0.0.0 by default
    assert cfg.port == 8765


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("BRAIN_VAULT", "/tmp/v")
    monkeypatch.setenv("BRAIN_DB", "/tmp/v/idx.db")
    monkeypatch.setenv("BRAIN_TOKEN", "secret")
    monkeypatch.setenv("BRAIN_HOST", "100.64.0.1")
    monkeypatch.setenv("BRAIN_PORT", "9000")
    cfg = load_config()
    assert cfg.vault == Path("/tmp/v")
    assert cfg.db == Path("/tmp/v/idx.db")
    assert cfg.token == "secret"
    assert cfg.host == "100.64.0.1"
    assert cfg.port == 9000


def test_db_defaults_under_vault(monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_DB", raising=False)
    monkeypatch.setenv("BRAIN_VAULT", str(tmp_path / "myvault"))
    cfg = load_config()
    assert cfg.db == tmp_path / "myvault" / ".brain" / "index.db"
