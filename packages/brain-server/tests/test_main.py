from __future__ import annotations

import brain_server.__main__ as main_mod
from brain_server.config import Config


def test_main_runs_uvicorn_with_configured_bind(monkeypatch, tmp_path):
    captured = {}

    def fake_run(app, host, port, log_level):
        captured.update(host=host, port=port, app=app)

    cfg = Config(vault=tmp_path, db=tmp_path / "i.db", token="t", host="127.0.0.1", port=8788)
    monkeypatch.setattr(main_mod, "load_config", lambda: cfg)
    monkeypatch.setattr(main_mod.uvicorn, "run", fake_run)
    # create_app builds the real app but lifespan only runs under a server, so
    # this stays cheap.
    main_mod.main()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8788
    assert captured["app"] is not None
