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
        self.error_calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))

    def error(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.error_calls.append((code, message, data))


class DummyExchange:
    def __init__(self, *, delay: float = 0.0, order=None, open_orders=None, cancel_exc: Exception | None = None) -> None:
        self.delay = delay
        self.order = order
        self.open_orders = list(open_orders or [])
        self.cancel_exc = cancel_exc
        self.create_calls = 0
        self.cancel_calls = 0
        self.fetch_order_calls = 0

    async def create_limit_order(self, **kwargs):
        self.create_calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return {'status': 'NEW', 'orderId': f'order-{self.create_calls}'}

    async def fetch_order(self, symbol: str, order_id=None, client_order_id=None):
        self.fetch_order_calls += 1
        if isinstance(self.order, list):
            result = self.order.pop(0)
        else:
            result = self.order
        if isinstance(result, Exception):
            raise result
        return result

    async def fetch_open_orders(self, symbol: str):
        return list(self.open_orders)

    async def cancel_order(self, **kwargs):
        self.cancel_calls += 1
        if self.cancel_exc is not None:
            raise self.cancel_exc
        return {'ok': True}


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
    max_daily_loss_pct: float = 2.0
    safe_mode_cooldown_min: int = 60
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


def make_engine(*, state: str = 'FLAT', pending: PendingOrder | None = None, position: Position | None = None, exchange: DummyExchange | None = None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = exchange or DummyExchange()
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.session.day_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    engine.runtime.balances = {
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
        'ETH': Balance(free=0.0108 if position else 0.0, locked=0.0, dust=0.0),
    }
    engine.runtime.pending = pending
    engine.runtime.position = position
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
    engine._closed_candles = [candle] * 30
    engine._latest_book = {'bestBid': 2315.49, 'bestAsk': 2315.59}
    engine._partial_fill_fingerprints = {}
    engine._fill_reconcile_fingerprints = {}
    engine._recent_signal_fps = {}
    engine._submit_lock = None
    engine._exit_submit_lock = None
    engine._save_runtime = lambda: None
    engine.sync_balances = _noop
    return engine


@pytest.mark.asyncio
async def test_concurrent_force_buy_submits_only_one_order() -> None:
    engine = make_engine(state='FLAT', exchange=DummyExchange(delay=0.05))

    await asyncio.gather(
        TradeBotEngine._submit_entry(engine, source='manual_force_buy'),
        TradeBotEngine._submit_entry(engine, source='manual_force_buy'),
    )

    assert engine.exchange.create_calls == 1
    assert engine.runtime.pending is not None
    assert engine.runtime.pending.side == 'BUY'
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'ENTRY_ALREADY_PENDING' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_cancel_pending_race_filled_commits_position_without_warning() -> None:
    pending = PendingOrder(side='BUY', price=2320.0, qty=0.0107, status='NEW', order_id='oid-1', client_order_id='cid-1', remaining_qty=0.0107)
    exchange = DummyExchange(
        order=[
            {'status': 'NEW', 'executedQty': '0.0', 'origQty': '0.0107', 'price': '2320.0'},
            {'status': 'FILLED', 'executedQty': '0.0107', 'origQty': '0.0107', 'price': '2320.0'},
        ],
        cancel_exc=RuntimeError('cancel race'),
    )
    engine = make_engine(state='BUY_PENDING', pending=pending, exchange=exchange)
    engine._latest_atr = lambda: 1.0

    await TradeBotEngine.cancel_pending(engine)

    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.state == 'IN_POSITION'
    assert any(call[0] == 'ORDER_CANCEL_RACE_FILLED' for call in engine.logger.info_calls)
    assert not any(call[0] == 'ORDER_CANCEL_WARN' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_partial_sell_fill_keeps_remaining_position_open() -> None:
    position = Position(qty=0.0108, entry_price=2315.0, source='manual_force_buy')
    pending = PendingOrder(side='SELL', price=2315.49, qty=0.0108, order_id='exit-1', client_order_id='cid-1', source='manual_force_sell')
    engine = make_engine(state='SELL_PENDING', pending=pending, position=position)

    await TradeBotEngine._commit_filled_pending(engine, pending, source='live_order', fill_price=2316.0, fill_qty=0.0050)

    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.position.qty == pytest.approx(0.0058)
    assert engine.runtime.state == 'IN_POSITION'
    assert engine.runtime.session.daily_trade_count == 0
    assert any(call[0] == 'ORDER_PARTIALLY_FILLED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_orphan_pending_cleanup_after_missing_threshold() -> None:
    pending = PendingOrder(side='BUY', price=2305.0, qty=0.0108, order_id='oid-1', client_order_id='cid-1', submitted_at=0, remaining_qty=0.0108, missing_count=2)
    engine = make_engine(state='BUY_PENDING', pending=pending, exchange=DummyExchange(order=RuntimeError('not found'), open_orders=[]))

    import tradebot.engine as engine_mod
    old_utc_ms = engine_mod.utc_ms
    engine_mod.utc_ms = lambda: 20_000
    try:
        await TradeBotEngine._reconcile_pending_order(engine)
    finally:
        engine_mod.utc_ms = old_utc_ms

    assert engine.runtime.pending is None
    assert engine.runtime.state == 'FLAT'
    assert any(call[0] == 'ORPHAN_PENDING_CLEANUP' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_exit_min_notional_is_blocked_without_submit() -> None:
    position = Position(qty=0.0001, entry_price=2315.0, source='manual_force_buy')
    engine = make_engine(state='IN_POSITION', position=position)
    engine.runtime.balances['ETH'] = Balance(free=0.0001, locked=0.0, dust=0.0)

    await TradeBotEngine._submit_exit(engine, source='manual_force_sell')

    assert engine.exchange.create_calls == 0
    assert engine.runtime.pending is None
    assert any(call[0] == 'EXIT_BLOCKED' and call[2]['skipCode'] == 'MIN_NOTIONAL_BLOCKED' for call in engine.logger.warn_calls)
