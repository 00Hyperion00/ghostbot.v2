from dataclasses import asdict
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tradebot.api import create_app
from tradebot.models import Candle, LogEvent
from tradebot.persistence import SQLiteStore


class DummyExchange:
    async def fetch_klines(self, symbol: str, interval: str, limit: int):
        return [
            Candle(open_time=1, close_time=2, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0, quote_volume=15.0),
            Candle(open_time=3, close_time=4, open=1.5, high=2.5, low=1.0, close=2.0, volume=12.0, quote_volume=20.0),
        ][:limit]


class DummyEngine:
    def __init__(self, store: SQLiteStore) -> None:
        self._running = True
        self.settings = SimpleNamespace(
            symbol='ETHUSDT',
            ai_provider_enabled=True,
            ai_provider_mode='local_xgboost',
            ai_model_path='models/x.json',
            ai_confidence_threshold=0.6,
            kline_interval='1m',
        )
        self.store = store
        self.exchange = DummyExchange()
        self.ai_provider = SimpleNamespace(available=True)

    async def get_status(self):
        return {'state': 'FLAT', 'symbol': 'ETHUSDT', 'ws_status': 'CONNECTED'}

    async def start(self):
        return None

    async def stop(self):
        return None

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



def test_api_logs_and_market_endpoints(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / 'api.db'))
    store.append_log(LogEvent(ts=10, level='INFO', code='ONE', message='first'))
    store.append_log(LogEvent(ts=20, level='INFO', code='TWO', message='second'))
    app = create_app(DummyEngine(store))
    client = TestClient(app)

    logs = client.get('/logs', params={'limit': 0, 'order': 'asc'})
    assert logs.status_code == 200
    assert [item['code'] for item in logs.json()] == ['ONE', 'TWO']

    klines = client.get('/market/klines', params={'symbol': 'ETHUSDT', 'interval': '1m', 'limit': 2})
    assert klines.status_code == 200
    assert klines.json()[0]['close'] == asdict(Candle(open_time=1, close_time=2, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0, quote_volume=15.0))['close']
