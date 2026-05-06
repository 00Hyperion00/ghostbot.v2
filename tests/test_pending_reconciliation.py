from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, PendingOrder, RuntimeState, SymbolRules


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
    def __init__(self, *, order=None, open_orders=None) -> None:
        self.order = order
        self.open_orders = list(open_orders or [])
        self.cancel_calls = 0

    async def fetch_order(self, symbol: str, order_id=None, client_order_id=None):
        if isinstance(self.order, Exception):
            raise self.order
        return self.order

    async def fetch_open_orders(self, symbol: str):
        return list(self.open_orders)

    async def cancel_order(self, **kwargs):
        self.cancel_calls += 1
        return {'ok': True}


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
    execution_mode: str = 'live_demo'
    order_timeout_sec: int = 20
    force_entry_price_mode: str = 'passive'
    force_exit_price_mode: str = 'aggressive'


async def _noop(*args, **kwargs):
    return None


def make_engine(*, state: str = 'BUY_PENDING', pending: PendingOrder | None = None, order=None, open_orders=None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = DummyExchange(order=order, open_orders=open_orders)
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.balances = {
        'ETH': Balance(free=0.0, locked=0.0, dust=0.0),
        'USDT': Balance(free=100.0, locked=0.0, dust=0.0),
    }
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
    engine._closed_candles = [Candle(open_time=1, close_time=2, open=2300, high=2310, low=2290, close=2305, volume=1.0, quote_volume=2305.0)]
    engine._latest_book = {'bestBid': 2305.0, 'bestAsk': 2305.1}
    engine._partial_fill_fingerprints = {}
    engine._save_runtime = lambda: None
    engine.sync_balances = _noop
    engine.runtime.pending = pending or PendingOrder(
        side='BUY',
        price=2305.0,
        qty=0.0108,
        status='NEW',
        order_id='oid-1',
        client_order_id='cid-1',
        submitted_at=1,
        remaining_qty=0.0108,
    )
    return engine


@pytest.mark.asyncio
async def test_reconcile_updates_partial_fill_snapshot_and_logs_partial_event():
    engine = make_engine(order={'status': 'PARTIALLY_FILLED', 'executedQty': '0.0040', 'origQty': '0.0108', 'price': '2305.0'})

    await TradeBotEngine._reconcile_pending_order(engine)

    pending = engine.runtime.pending
    assert pending is not None
    assert pending.status == 'PARTIALLY_FILLED'
    assert pending.partial_executed_qty == pytest.approx(0.0040)
    assert pending.remaining_qty == pytest.approx(0.0068)
    assert any(call[0] == 'PENDING_RECONCILE_PARTIAL' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_reconcile_not_found_respects_grace_window_and_keeps_pending():
    pending = PendingOrder(side='BUY', price=2305.0, qty=0.0108, order_id='oid-1', client_order_id='cid-1', submitted_at=0, remaining_qty=0.0108)
    engine = make_engine(pending=pending, order=RuntimeError('missing'), open_orders=[])
    TradeBotEngine._pending_grace_window_ms(engine)

    # keep current time effectively near submit time
    import tradebot.engine as engine_mod
    old_utc_ms = engine_mod.utc_ms
    engine_mod.utc_ms = lambda: 2_000
    try:
        await TradeBotEngine._reconcile_pending_order(engine)
    finally:
        engine_mod.utc_ms = old_utc_ms

    assert engine.runtime.pending is not None
    assert engine.runtime.pending.missing_count == 1
    assert any(call[0] == 'PENDING_RECONCILE_NOT_FOUND' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_reconcile_cleans_orphan_pending_after_missing_threshold():
    pending = PendingOrder(side='BUY', price=2305.0, qty=0.0108, order_id='oid-1', client_order_id='cid-1', submitted_at=0, remaining_qty=0.0108, missing_count=2)
    engine = make_engine(pending=pending, order=RuntimeError('missing'), open_orders=[])

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
async def test_reconcile_requests_cancel_for_still_open_orphan_after_timeout():
    pending = PendingOrder(side='BUY', price=2305.0, qty=0.0108, order_id='oid-1', client_order_id='cid-1', submitted_at=0, remaining_qty=0.0108, reconcile_attempts=9)
    engine = make_engine(pending=pending, order=RuntimeError('missing'), open_orders=[{'orderId': 'oid-1', 'clientOrderId': 'cid-1'}])

    import tradebot.engine as engine_mod
    old_utc_ms = engine_mod.utc_ms
    engine_mod.utc_ms = lambda: 30_000
    try:
        await TradeBotEngine._reconcile_pending_order(engine)
    finally:
        engine_mod.utc_ms = old_utc_ms

    assert engine.runtime.pending is not None
    assert engine.runtime.pending.cancel_requested is True
    assert engine.exchange.cancel_calls == 1
    assert any(call[0] == 'RECONCILIATION_DEFERRED' for call in engine.logger.warn_calls)
