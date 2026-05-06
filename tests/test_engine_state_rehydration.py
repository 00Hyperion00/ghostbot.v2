from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tradebot.config import Settings
from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Position, SymbolRules
from tradebot.persistence import SQLiteStore


class DummyExchange:
    def __init__(self, balances: dict[str, Balance], rules: SymbolRules) -> None:
        self._balances = balances
        self._rules = rules

    async def fetch_symbol_rules(self, symbol: str) -> SymbolRules:
        return self._rules

    async def fetch_balances(self) -> dict[str, Balance]:
        return self._balances

    async def fetch_klines(self, symbol: str, interval: str, limit: int):
        return []

    async def close(self) -> None:
        return None

    async def stream_market(self):
        if False:
            yield None
        return


@pytest.mark.asyncio
async def test_start_rehydrates_runtime_state_from_persisted_position(tmp_path: Path):
    db_path = tmp_path / 'tradebot.db'
    store = SQLiteStore(str(db_path))
    store.set_json('runtime', {
        'state': 'FLAT',
        'symbol': 'ETHUSDT',
        'position': {
            'qty': 0.0108,
            'entry_price': 2307.74,
            'source': 'manual_force_buy',
            'order_id': '123',
            'client_order_id': 'abc',
            'opened_at': 1776683300000,
            'risk_plan': None,
        },
    })
    settings = Settings(symbol='ETHUSDT', ai_provider_enabled=False, database_path=str(db_path))
    engine = TradeBotEngine(settings, store)
    rules = SymbolRules('ETHUSDT', 'ETH', 'USDT', 0.01, 0.0001, 0.0001, 1000.0, 5.0)
    balances = {
        'ETH': Balance(free=0.0108, locked=0.0, dust=0.0),
        'USDT': Balance(free=4975.0, locked=0.0, dust=0.0),
    }
    engine.exchange = DummyExchange(balances, rules)

    async def fake_market_loop() -> None:
        await asyncio.sleep(3600)

    async def fake_reconcile_loop() -> None:
        await asyncio.sleep(3600)

    engine._market_loop = fake_market_loop
    engine._reconcile_loop = fake_reconcile_loop

    started = await engine.start()

    assert started is True
    assert engine.runtime.state == 'IN_POSITION'
    assert engine.runtime.position is not None
    assert engine.runtime.position.qty == pytest.approx(0.0108)

    await engine.stop()


@pytest.mark.asyncio
async def test_start_recovers_position_from_live_balance_when_runtime_position_missing(tmp_path: Path):
    db_path = tmp_path / 'tradebot.db'
    store = SQLiteStore(str(db_path))
    store.set_json('runtime', {'state': 'STOPPED', 'symbol': 'ETHUSDT'})
    settings = Settings(symbol='ETHUSDT', ai_provider_enabled=False, database_path=str(db_path))
    engine = TradeBotEngine(settings, store)
    rules = SymbolRules('ETHUSDT', 'ETH', 'USDT', 0.01, 0.0001, 0.0001, 1000.0, 5.0)
    balances = {
        'ETH': Balance(free=0.0108, locked=0.0, dust=0.0),
        'USDT': Balance(free=4975.0, locked=0.0, dust=0.0),
    }
    engine.exchange = DummyExchange(balances, rules)

    async def fake_market_loop() -> None:
        await asyncio.sleep(3600)

    async def fake_reconcile_loop() -> None:
        await asyncio.sleep(3600)

    engine._market_loop = fake_market_loop
    engine._reconcile_loop = fake_reconcile_loop

    started = await engine.start()

    assert started is True
    assert engine.runtime.state == 'IN_POSITION'
    assert engine.runtime.position is not None
    assert engine.runtime.position.source == 'recovered_balance'
    assert engine.runtime.position.qty == pytest.approx(0.0108)

    await engine.stop()



@pytest.mark.asyncio
async def test_start_clears_stale_position_when_live_balance_is_effectively_zero(tmp_path: Path):
    db_path = tmp_path / 'tradebot.db'
    store = SQLiteStore(str(db_path))
    store.set_json('runtime', {
        'state': 'IN_POSITION',
        'symbol': 'ETHUSDT',
        'position': {
            'qty': 0.0108,
            'entry_price': 2307.74,
            'source': 'manual_force_buy',
            'order_id': '123',
            'client_order_id': 'abc',
            'opened_at': 1776683300000,
            'risk_plan': None,
        },
    })
    settings = Settings(symbol='ETHUSDT', ai_provider_enabled=False, database_path=str(db_path))
    engine = TradeBotEngine(settings, store)
    rules = SymbolRules('ETHUSDT', 'ETH', 'USDT', 0.01, 0.0001, 0.0001, 1000.0, 5.0)
    balances = {
        'ETH': Balance(free=0.0, locked=0.0, dust=0.0),
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
    }
    engine.exchange = DummyExchange(balances, rules)

    async def fake_market_loop() -> None:
        await asyncio.sleep(3600)

    async def fake_reconcile_loop() -> None:
        await asyncio.sleep(3600)

    engine._market_loop = fake_market_loop
    engine._reconcile_loop = fake_reconcile_loop

    started = await engine.start()

    assert started is True
    assert engine.runtime.state == 'FLAT'
    assert engine.runtime.position is None

    await engine.stop()
