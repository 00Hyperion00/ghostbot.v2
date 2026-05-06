from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from tradebot.api import create_app


class DummyEngine:
    def __init__(self, *, start_result: bool = False, stop_result: bool = False) -> None:
        self._running = True
        self.settings = SimpleNamespace(symbol='SOLUSDT')
        self.runtime = SimpleNamespace(state='FLAT')
        self._start_result = start_result
        self._stop_result = stop_result
        self.start_calls = 0
        self.stop_calls = 0
        self.store = SimpleNamespace(fetch_logs=lambda limit=200: [])

    async def get_status(self) -> dict:
        return {'state': self.runtime.state, 'symbol': self.settings.symbol}

    async def start(self) -> bool:
        self.start_calls += 1
        return self._start_result

    async def stop(self) -> bool:
        self.stop_calls += 1
        return self._stop_result

    async def force_buy(self) -> None:
        return None

    async def force_sell(self) -> None:
        return None

    async def cancel_pending(self) -> None:
        return None

    async def sync_balances(self) -> None:
        return None

    async def risk_reset(self) -> None:
        return None

    async def toggle_safe_mode(self) -> None:
        return None


def test_start_endpoint_reports_already_running_when_engine_returns_false():
    engine = DummyEngine(start_result=False)
    client = TestClient(create_app(engine))

    payload = client.post('/start').json()

    assert payload['ok'] is True
    assert payload['started'] is False
    assert payload['already_running'] is True
    assert engine.start_calls == 1


def test_stop_endpoint_reports_already_stopped_when_engine_returns_false():
    engine = DummyEngine(stop_result=False)
    client = TestClient(create_app(engine))

    payload = client.post('/stop').json()

    assert payload['ok'] is True
    assert payload['stopped'] is False
    assert payload['already_stopped'] is True
    assert engine.stop_calls == 1
