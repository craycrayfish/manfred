from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from brain_server.config import Config
from brain_server.index import Index

# Plugin scripts live outside the server package (they ship with the Claude Code
# plugin) and have no package context, so load them by path like the CLI tests.
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "plugins" / "brain" / "scripts"


def load_script(name: str):
    """Load plugins/brain/scripts/<name>.py as an isolated module."""
    path = SCRIPTS_DIR / f"{name}.py"
    loader = SourceFileLoader(f"brain_{name}", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "brain-vault"
    for d in ("inbox", "longterm", "archive", ".brain"):
        (v / d).mkdir(parents=True)
    return v


@pytest.fixture
def index(vault: Path) -> Index:
    idx = Index(vault / ".brain" / "index.db")
    yield idx
    idx.close()


@pytest.fixture
def cfg(vault: Path) -> Config:
    return Config(
        vault=vault,
        db=vault / ".brain" / "index.db",
        token="testtoken",
        host="127.0.0.1",
        port=8765,
    )
