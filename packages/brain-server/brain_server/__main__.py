"""Entrypoint: ``python -m brain_server`` runs the uvicorn server.

Binds to BRAIN_HOST (default loopback) — the launchd plist sets it to the
tailnet IP. Never bind 0.0.0.0; the brain is tailnet-private.
"""

from __future__ import annotations

import uvicorn

from .api import create_app
from .config import load_config


def main() -> None:
    cfg = load_config()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
