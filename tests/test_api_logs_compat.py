from __future__ import annotations

from fastapi.testclient import TestClient

from tradebot.api import create_app


class DummyStore:
    def fetch_logs(self, limit: int = 200):
        return [{'ts': 2}, {'ts': 1}][:limit]


class DummySettings:
    symbol = 'ETHUSDT'
    ai_provider_enabled = False
    ai_provider_mode = 'local_xgboost'
    ai_model_path = 'models/x.ubj'
    ai_confidence_threshold = 0.6
    def to_dict(self):
        return {}


class DummyExchange:
    async def fetch_klines(self, symbol: str, interval: str, limit: int):
        return []


class DummyEngine:
    def __init__(self):
        self.settings = DummySettings()
        self.store = DummyStore()
        self.exchange = DummyExchange()
        self.ai_provider = None
        self._running = False
    async def get_status(self):
        return {}
    async def start(self):
        return True
    async def stop(self):
        return True
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


def test_logs_endpoint_falls_back_when_store_does_not_accept_order() -> None:
    client = TestClient(create_app(DummyEngine()))
    payload = client.get('/logs?limit=2&order=desc').json()
    assert payload == [{'ts': 1}, {'ts': 2}]
