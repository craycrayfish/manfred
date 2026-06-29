"""Runtime configuration, resolved from environment variables.

All knobs are env-driven so the launchd plist (and tests) can inject them
without touching code. Defaults are safe for a local dev run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    vault: Path
    db: Path
    token: str
    host: str
    port: int


def load_config() -> Config:
    """Build a Config from BRAIN_* environment variables."""
    vault = Path(os.environ.get("BRAIN_VAULT", str(Path.home() / "brain-vault"))).expanduser()
    db_default = vault / ".brain" / "index.db"
    db = Path(os.environ.get("BRAIN_DB", str(db_default))).expanduser()
    token = os.environ.get("BRAIN_TOKEN", "")
    # Bind to loopback by default; deploy sets the tailnet IP. Never 0.0.0.0.
    host = os.environ.get("BRAIN_HOST", "127.0.0.1")
    port = int(os.environ.get("BRAIN_PORT", "8765"))
    return Config(vault=vault, db=db, token=token, host=host, port=port)
