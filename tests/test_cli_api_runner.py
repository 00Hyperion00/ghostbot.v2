from __future__ import annotations

from tradebot import cli as cli_module


class DummySettings:
    pass


def test_run_api_uses_managed_app_and_uvicorn(monkeypatch):
    calls = {}

    def fake_create_managed_app(settings):
        calls['settings'] = settings
        return 'app'

    def fake_run(app, **kwargs):
        calls['app'] = app
        calls['kwargs'] = kwargs

    monkeypatch.setattr(cli_module, 'create_managed_app', fake_create_managed_app)
    monkeypatch.setattr(cli_module.uvicorn, 'run', fake_run)

    cli_module.run_api(DummySettings(), '127.0.0.1', 8787)

    assert calls['app'] == 'app'
    assert calls['kwargs']['host'] == '127.0.0.1'
    assert calls['kwargs']['port'] == 8787
    assert calls['kwargs']['lifespan'] == 'on'
