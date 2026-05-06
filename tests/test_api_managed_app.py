from __future__ import annotations

from fastapi.testclient import TestClient

from tradebot import api as api_module


class DummySettings:
    database_path = ':memory:'
    symbol = 'ETHUSDT'


class DummyStore:
    def __init__(self, path: str) -> None:
        self.path = path

    def fetch_logs(self, limit: int = 200):
        return []


class DummyEngine:
    def __init__(self, settings, store) -> None:
        self.settings = settings
        self.store = store
        self._running = True
        self.started = 0
        self.closed = 0
        self.runtime = type('R', (), {'state': 'FLAT'})()

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


def test_create_managed_app_starts_and_closes_engine(monkeypatch):
    created = []

    monkeypatch.setattr(api_module, 'SQLiteStore', DummyStore)

    def build_engine(settings, store):
        engine = DummyEngine(settings, store)
        created.append(engine)
        return engine

    monkeypatch.setattr(api_module, 'TradeBotEngine', build_engine)

    app = api_module.create_managed_app(DummySettings())
    with TestClient(app) as client:
        payload = client.get('/health').json()
        assert payload['ok'] is True
        assert payload['symbol'] == 'ETHUSDT'

    assert len(created) == 1
    assert created[0].started == 1
    assert created[0].closed == 1
