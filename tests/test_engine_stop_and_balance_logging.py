from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance


class DummyLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict, int | None]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.calls.append((code, message, data, dedupe_ms))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.calls.append((code, message, data, dedupe_ms))


@pytest.mark.asyncio
async def test_stop_returns_without_waiting_for_stuck_tasks() -> None:
    engine = object.__new__(TradeBotEngine)
    engine.runtime = SimpleNamespace(state='FLAT', ws_status='CONNECTED', pending=None)
    engine.logger = DummyLogger()
    engine._running = True
    engine._save_runtime = lambda: None

    started = asyncio.Event()

    async def stubborn() -> None:
        started.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await asyncio.sleep(3600)

    engine._market_task = asyncio.create_task(stubborn())
    engine._reconcile_task = asyncio.create_task(stubborn())

    await started.wait()
    stopped = await TradeBotEngine.stop(engine)

    assert stopped is True
    assert engine.runtime.state == 'STOPPED'
    assert engine._market_task is None
    assert engine._reconcile_task is None
    assert any(call[0] == 'TASK_CANCEL_TIMEOUT' for call in engine.logger.calls)


@pytest.mark.asyncio
async def test_sync_balances_skips_duplicate_balances_ready_logs() -> None:
    engine = object.__new__(TradeBotEngine)
    engine.logger = DummyLogger()
    engine.symbol_rules = SimpleNamespace(base_asset='SOL', quote_asset='USDT', step_size=0.001)
    engine.runtime = SimpleNamespace(balances={}, dust_snapshot={})
    engine._save_runtime = lambda: None

    async def fetch_balances() -> dict[str, Balance]:
        return {
            'SOL': Balance(free=0.1, locked=0.0, dust=0.0),
            'USDT': Balance(free=100.0, locked=0.0, dust=0.0),
        }

    engine.exchange = SimpleNamespace(fetch_balances=fetch_balances)

    await TradeBotEngine.sync_balances(engine)
    await TradeBotEngine.sync_balances(engine)

    balance_logs = [c for c in engine.logger.calls if c[0] == 'BALANCES_READY']
    assert len(balance_logs) == 1
    assert balance_logs[0][2]['changed'] is True
