from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, PendingOrder, Position, RuntimeState, SymbolRules


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
        return {'status': 'NEW', 'orderId': f'exit-{self.create_calls}'}


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
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


def make_engine(state: str = 'IN_POSITION') -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = DummyExchange()
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.session.day_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    engine.runtime.balances = {
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
        'ETH': Balance(free=0.0108, locked=0.0, dust=0.0),
    }
    engine.runtime.position = Position(qty=0.0108, entry_price=2315.0, source='manual_force_buy', order_id='entry-1') if state in {'IN_POSITION', 'SELL_PENDING'} else None
    engine.symbol_rules = SymbolRules(
        symbol='ETHUSDT',
        base_asset='ETH',
        quote_asset='USDT',
        tick_size=0.01,
        step_size=0.0001,
        min_qty=0.0001,
        max_qty=100000.0,
        min_notional=5.0,
    )
    candle = Candle(open_time=1, close_time=2, open=2310.0, high=2316.0, low=2308.0, close=2315.5, volume=1.0, quote_volume=2315.5)
    engine._closed_candles = [candle]
    engine._latest_book = {'bestBid': 2315.49, 'bestAsk': 2315.59}
    engine._save_runtime = lambda: None
    engine.sync_balances = _noop
    engine._submit_lock = None
    engine._exit_submit_lock = None
    return engine


def test_exit_guard_reasons_are_deterministic():
    engine = make_engine(state='STOPPED')
    engine.runtime.position = None
    assert TradeBotEngine._exit_guard(engine) == (False, 'ENGINE_STOPPED')

    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.balances['ETH'] = Balance(free=0.0, locked=0.0, dust=0.0)
    assert TradeBotEngine._exit_guard(engine) == (False, 'POSITION_NOT_FOUND')

    engine = make_engine(state='SELL_PENDING')
    engine.runtime.pending = PendingOrder(side='SELL', price=2315.49, qty=0.0108)
    assert TradeBotEngine._exit_guard(engine) == (False, 'EXIT_ALREADY_PENDING')


@pytest.mark.asyncio
async def test_submit_exit_is_serialized_and_second_attempt_is_blocked():
    engine = make_engine(state='IN_POSITION')
    engine.exchange = DummyExchange(delay=0.05)

    await asyncio.gather(
        TradeBotEngine._submit_exit(engine, source='manual_force_sell'),
        TradeBotEngine._submit_exit(engine, source='manual_force_sell'),
    )

    assert engine.exchange.create_calls == 1
    assert engine.runtime.pending is not None
    assert engine.runtime.pending.side == 'SELL'
    assert engine.runtime.state == 'SELL_PENDING'
    assert any(call[0] == 'EXIT_BLOCKED' and call[2]['skipCode'] == 'EXIT_ALREADY_PENDING' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_sell_fill_closes_position_and_updates_stats():
    engine = make_engine(state='SELL_PENDING')
    pending = PendingOrder(side='SELL', price=2315.49, qty=0.0108, order_id='oid-1', client_order_id='cid-1', source='manual_force_sell')
    engine.runtime.pending = pending

    await TradeBotEngine._commit_filled_pending(engine, pending, source='live_order', fill_price=2316.0, fill_qty=0.0108)

    assert engine.runtime.pending is None
    assert engine.runtime.position is None
    assert engine.runtime.state == 'FLAT'
    assert engine.runtime.session.daily_trade_count == 1
    assert engine.runtime.session.daily_realized_pnl == pytest.approx((2316.0 - 2315.0) * 0.0108)
    assert any(call[0] == 'POSITION_CLOSED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_sell_pending_cancel_returns_to_in_position():
    engine = make_engine(state='SELL_PENDING')
    pending = PendingOrder(side='SELL', price=2315.49, qty=0.0108, order_id='oid-1', client_order_id='cid-1', source='manual_force_sell')
    engine.runtime.pending = pending

    await TradeBotEngine._clear_pending(engine, 'LIVE_CANCELED', pending)

    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.state == 'IN_POSITION'
    assert any(call[0] == 'ORDER_CANCELED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_partial_sell_fill_keeps_position_open_and_does_not_close_trade():
    engine = make_engine(state='SELL_PENDING')
    pending = PendingOrder(side='SELL', price=2315.49, qty=0.0108, order_id='oid-1', client_order_id='cid-1', source='manual_force_sell')
    engine.runtime.pending = pending

    await TradeBotEngine._commit_filled_pending(engine, pending, source='live_order', fill_price=2316.0, fill_qty=0.0050)

    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.position.qty == pytest.approx(0.0058)
    assert engine.runtime.state == 'IN_POSITION'
    assert engine.runtime.session.daily_trade_count == 0
    assert not any(call[0] == 'POSITION_CLOSED' for call in engine.logger.info_calls)
    assert any(call[0] == 'ORDER_PARTIALLY_FILLED' for call in engine.logger.info_calls)
