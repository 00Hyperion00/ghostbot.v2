from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, PendingOrder, RuntimeState, SymbolRules


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str, dict]] = []
        self.warn_calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))

    def error(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))


class DummyExchange:
    def __init__(self, *, delay: float = 0.0) -> None:
        self.delay = delay
        self.create_calls = 0

    async def create_limit_order(self, **kwargs):
        self.create_calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return {'status': 'NEW', 'orderId': f'oid-{self.create_calls}'}


@dataclass
class DummySettings:
    symbol: str = 'SOLUSDT'
    execution_mode: str = 'live_demo'
    order_notional_usd: float = 25.0
    min_notional_buffer_multiplier: float = 1.10
    force_entry_price_mode: str = 'passive'
    force_exit_price_mode: str = 'aggressive'
    sizing_mode: str = 'fixed_quote'
    auto_trade_cooldown_sec: int = 5
    max_daily_trades: int = 0
    max_consecutive_losses: int = 3
    atr_period: int = 14
    risk_reward_ratio: float = 2.0
    atr_multiplier: float = 1.5
    fixed_stop_loss_pct: float = 1.0
    fixed_take_profit_pct: float = 2.0
    tp_mode: str = 'rr'
    sl_mode: str = 'atr'
    break_even_enabled: bool = True
    break_even_trigger_r: float = 1.0
    break_even_buffer_pct: float = 0.02
    trailing_stop_enabled: bool = True
    trailing_atr_multiplier: float = 1.0
    trailing_only_after_break_even: bool = True
    partial_take_profit_enabled: bool = True
    partial_take_profit_rr: float = 1.0
    partial_take_profit_close_pct: float = 50.0
    order_timeout_sec: int = 20
    auto_trade_on_signal: bool = True
    auto_trade_signal_mode: str = 'normal'


async def _noop(*args, **kwargs):
    return None


def make_engine(state: str = 'FLAT') -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = DummyExchange()
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='SOLUSDT')
    engine.runtime.session.day_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    engine.runtime.balances = {
        'USDT': Balance(free=100.0, locked=0.0, dust=0.0),
        'SOL': Balance(free=0.0, locked=0.0, dust=0.0),
    }
    engine.symbol_rules = SymbolRules(
        symbol='SOLUSDT',
        base_asset='SOL',
        quote_asset='USDT',
        tick_size=0.01,
        step_size=0.001,
        min_qty=0.001,
        max_qty=100000.0,
        min_notional=5.0,
    )
    candle = Candle(open_time=1, close_time=2, open=84.5, high=84.6, low=84.4, close=84.55, volume=1.0, quote_volume=84.55)
    engine._closed_candles = [candle]
    engine._latest_book = {'bestBid': 84.55, 'bestAsk': 84.56}
    engine._save_runtime = lambda: None
    engine.sync_balances = _noop
    engine._day_key = lambda: '2026-04-20'
    engine._submit_lock = None
    return engine


def test_entry_guard_reasons_are_deterministic():
    engine = make_engine(state='STOPPED')
    assert TradeBotEngine._entry_guard(engine) == (False, 'ENGINE_STOPPED')

    engine = make_engine(state='BUY_PENDING')
    assert TradeBotEngine._entry_guard(engine) == (False, 'INVALID_ENTRY_STATE_BUY_PENDING')

    engine = make_engine(state='FLAT')
    engine.runtime.pending = PendingOrder(side='BUY', price=84.55, qty=0.295)
    assert TradeBotEngine._entry_guard(engine) == (False, 'ENTRY_ALREADY_PENDING')


@pytest.mark.asyncio
async def test_submit_entry_is_serialized_and_second_attempt_is_blocked():
    engine = make_engine(state='FLAT')
    engine.exchange = DummyExchange(delay=0.05)

    await asyncio.gather(
        TradeBotEngine._submit_entry(engine, source='manual_force_buy'),
        TradeBotEngine._submit_entry(engine, source='manual_force_buy'),
    )

    assert engine.exchange.create_calls == 1
    assert engine.runtime.pending is not None
    assert engine.runtime.pending.side == 'BUY'
    assert engine.runtime.state == 'BUY_PENDING'
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'ENTRY_ALREADY_PENDING' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_buy_fill_moves_runtime_to_in_position():
    engine = make_engine(state='BUY_PENDING')
    pending = PendingOrder(side='BUY', price=84.55, qty=0.295, order_id='oid-1', client_order_id='cid-1', source='manual_force_buy')
    engine.runtime.pending = pending
    engine._latest_atr = lambda: 0.5

    await TradeBotEngine._commit_filled_pending(engine, pending, source='live_order', fill_price=84.55, fill_qty=0.295)

    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.position.qty == pytest.approx(0.295)
    assert engine.runtime.state == 'IN_POSITION'


@pytest.mark.asyncio
async def test_buy_pending_cancel_returns_runtime_to_flat():
    engine = make_engine(state='BUY_PENDING')
    pending = PendingOrder(side='BUY', price=84.55, qty=0.295, order_id='oid-1', client_order_id='cid-1', source='manual_force_buy')
    engine.runtime.pending = pending

    await TradeBotEngine._clear_pending(engine, 'LIVE_CANCELED', pending)

    assert engine.runtime.pending is None
    assert engine.runtime.state == 'FLAT'
    assert any(call[0] == 'ORDER_CANCELED' for call in engine.logger.warn_calls)
