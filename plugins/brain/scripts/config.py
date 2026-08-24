"""Host/token resolution for the brain plugin hooks and skills.

Mirrors the precedence baked into `bin/brain` so the hook scripts and the CLI
always agree on which server to talk to:

    1. BRAIN_URL / BRAIN_TOKEN environment variables
    2. plugins/brain/brain.local.json   (gitignored, per-machine host)
    3. ~/.brain/config.json
    4. default http://localhost:8765 (no token)

The hook scripts shell out to `bin/brain` (which self-resolves), so they mainly
need `brain_cli()`. `resolve_config()` is provided for parity and any direct
HTTP use.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_URL = "http://localhost:8765"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_LOCAL = PLUGIN_ROOT / "brain.local.json"
HOME_CONFIG = Path.home() / ".brain" / "config.json"


def brain_cli() -> Path:
    """Absolute path to the bundled `brain` CLI (ships in the same plugin)."""
    return PLUGIN_ROOT / "bin" / "brain"


def resolve_config() -> tuple[str, str]:
    url = os.environ.get("BRAIN_URL")
    token = os.environ.get("BRAIN_TOKEN")
    if url:
        return url.rstrip("/"), token or ""
    for cfg_path in (PLUGIN_LOCAL, HOME_CONFIG):
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            return data.get("url", DEFAULT_URL).rstrip("/"), token or data.get("token", "")
    return DEFAULT_URL, token or ""
