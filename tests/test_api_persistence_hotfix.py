from __future__ import annotations

from fastapi.testclient import TestClient

from tradebot import api as api_module


class DummySettings:
    database_path = ':memory:'
    symbol = 'ETHUSDT'
    ai_provider_enabled = False
    ai_provider_mode = 'local_xgboost'
    ai_model_path = 'models/test.ubj'
    ai_confidence_threshold = 0.6

    def to_dict(self):
        return {'symbol': self.symbol}


class DummyStore:
    def __init__(self, path: str) -> None:
        self.path = path

    def fetch_logs(self, limit: int = 200):
        return [{'ts': 1, 'level': 'INFO', 'code': 'A', 'message': 'x', 'data': {}}]


class DummyEngine:
    def __init__(self, settings, store) -> None:
        self.settings = settings
        self.store = store
        self._running = True
        self.started = 0
        self.closed = 0
        self.runtime = type('R', (), {'state': 'FLAT'})()
        self.ai_provider = None

    async def start(self):
        self.started += 1

    async def close(self):
        self.closed += 1

    async def get_status(self):
        return {'state': 'FLAT', 'symbol': self.settings.symbol}

    async def force_buy(self):
        return None

    async def force_sell(self):
        return None

    async def cancel_pending(self):
        return None

    async def sync_balances(self):
        return None

    async def risk_reset(self):
        return None

    async def toggle_safe_mode(self):
        return None


class FailingEngine(DummyEngine):
    async def start(self):
        self.started += 1
        raise RuntimeError('bootstrap failed')


def test_create_managed_app_starts_and_closes_engine(monkeypatch):
    created = []
    monkeypatch.setattr(api_module, 'SQLiteStore', DummyStore)

    def factory(settings, store):
        engine = DummyEngine(settings, store)
        created.append(engine)
        return engine

    monkeypatch.setattr(api_module, 'TradeBotEngine', factory)
    app = api_module.create_managed_app(DummySettings())
    with TestClient(app) as client:
        health = client.get('/health').json()
        status = client.get('/status').json()
        assert health['ok'] is True
        assert health['bootstrap_ok'] is True
        assert status['symbol'] == 'ETHUSDT'
    assert created[0].started == 1
    assert created[0].closed == 1


def test_create_managed_app_degraded_health_when_engine_start_fails(monkeypatch):
    monkeypatch.setattr(api_module, 'SQLiteStore', DummyStore)
    monkeypatch.setattr(api_module, 'TradeBotEngine', FailingEngine)
    app = api_module.create_managed_app(DummySettings())
    with TestClient(app) as client:
        health = client.get('/health').json()
        status = client.get('/status').json()
        logs = client.get('/logs').json()
        assert health['ok'] is False
        assert health['degraded'] is True
        assert 'bootstrap failed' in health['start_error']
        assert status['state'] == 'STOPPED'
        assert logs and logs[0]['code'] == 'A'
