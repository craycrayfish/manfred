"""Tests for plugins/brain/scripts/config.py — host resolution + CLI locator.

Mirrors the precedence of bin/brain so hooks and the CLI agree on the host.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import load_script


@pytest.fixture
def config_mod():
    return load_script("config")


def test_brain_cli_points_at_plugin_bin(config_mod):
    p = config_mod.brain_cli()
    assert p.name == "brain"
    assert p.parent.name == "bin"
    assert p.exists()  # the CLI ships in the same plugin


def test_resolve_env_wins(config_mod, monkeypatch):
    monkeypatch.setenv("BRAIN_URL", "http://env-host:1/")
    monkeypatch.setenv("BRAIN_TOKEN", "envtoken")
    assert config_mod.resolve_config() == ("http://env-host:1", "envtoken")


def test_resolve_local_file_then_home(config_mod, monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_URL", raising=False)
    monkeypatch.delenv("BRAIN_TOKEN", raising=False)
    local = tmp_path / "brain.local.json"
    local.write_text(json.dumps({"url": "http://local:2", "token": "lt"}))
    monkeypatch.setattr(config_mod, "PLUGIN_LOCAL", local)
    monkeypatch.setattr(config_mod, "HOME_CONFIG", tmp_path / "nope.json")
    assert config_mod.resolve_config() == ("http://local:2", "lt")


def test_resolve_default_when_nothing(config_mod, monkeypatch, tmp_path):
    monkeypatch.delenv("BRAIN_URL", raising=False)
    monkeypatch.delenv("BRAIN_TOKEN", raising=False)
    monkeypatch.setattr(config_mod, "PLUGIN_LOCAL", tmp_path / "a.json")
    monkeypatch.setattr(config_mod, "HOME_CONFIG", tmp_path / "b.json")
    assert config_mod.resolve_config() == (config_mod.DEFAULT_URL, "")
