from __future__ import annotations

import asyncio

from tradebot.config import Settings
from tradebot.engine import TradeBotEngine
from tradebot.persistence import SQLiteStore


class DummyExchange:
    def __init__(self) -> None:
        self.closed = 0

    async def close(self) -> None:
        self.closed += 1


async def _sleeper():
    try:
        while True:
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        raise


def test_engine_close_cancels_tasks_and_closes_exchange(tmp_path):
    settings = Settings(
        api_key='',
        api_secret='',
        base_url='https://api.binance.com',
        symbol='ETHUSDT',
        market_type='spot_demo',
        kline_interval='1m',
        order_notional_usd=25.0,
        execution_mode='dry_run',
        ai_provider_enabled=False,
    )
    store = SQLiteStore(str(tmp_path / 'test.db'))
    engine = TradeBotEngine(settings, store)
    engine.exchange = DummyExchange()
    engine._running = True

    async def runner():
        engine._market_task = asyncio.create_task(_sleeper())
        engine._reconcile_task = asyncio.create_task(_sleeper())
        await engine.close()
        return engine.exchange.closed, engine._market_task, engine._reconcile_task

    closed_count, market_task, reconcile_task = asyncio.run(runner())
    assert closed_count == 1
    assert market_task is None
    assert reconcile_task is None
