from __future__ import annotations

from pathlib import Path

import pytest

from brain_server.config import Config
from brain_server.index import Index


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
