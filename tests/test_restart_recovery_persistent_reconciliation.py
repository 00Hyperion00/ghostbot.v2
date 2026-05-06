from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, PendingOrder, Position, RuntimeState, SymbolRules


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str, dict]] = []
        self.warn_calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, **kwargs) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, **kwargs) -> None:
        self.warn_calls.append((code, message, data))


class DummyExchange:
    def __init__(self, open_orders: list[dict] | None = None) -> None:
        self.open_orders = open_orders or []

    async def fetch_open_orders(self, symbol: str = 'ETHUSDT') -> list[dict]:
        return self.open_orders


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
    min_notional_buffer_multiplier: float = 1.0
    atr_period: int = 14
    risk_reward_ratio: float = 2.0
    atr_multiplier: float = 1.5
    fixed_stop_loss_pct: float = 1.0
    fixed_take_profit_pct: float = 2.0
    tp_mode: str = 'rr'
    sl_mode: str = 'atr'
    break_even_trigger_r: float = 1.0
    break_even_buffer_pct: float = 0.02
    trailing_stop_enabled: bool = True
    partial_take_profit_rr: float = 1.0
    partial_take_profit_close_pct: float = 50.0


def make_engine(*, open_orders: list[dict] | None = None, base_free: float = 0.0) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = DummyExchange(open_orders)
    engine.runtime = RuntimeState(state='STOPPED', ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.balances = {
        'ETH': Balance(free=base_free, locked=0.0, dust=0.0),
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
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
    engine._latest_book = {'bestBid': 2250.0, 'bestAsk': 2250.1}
    engine._closed_candles = []
    engine._save_runtime = lambda: None
    return engine


@pytest.mark.asyncio
async def test_startup_recovery_recovers_live_open_order_as_pending() -> None:
    engine = make_engine(open_orders=[{
        'symbol': 'ETHUSDT',
        'side': 'BUY',
        'status': 'PARTIALLY_FILLED',
        'orderId': 12345,
        'clientOrderId': 'cid-recover-1',
        'price': '2250.00',
        'origQty': '0.0100',
        'executedQty': '0.0040',
        'time': 1000,
    }])

    snapshot = await TradeBotEngine._startup_reconcile_persistent_state(engine)

    assert snapshot['pending_action'] == 'RECOVERED_LIVE_OPEN_ORDER'
    assert snapshot['open_order_count'] == 1
    assert engine.runtime.pending is not None
    assert engine.runtime.pending.side == 'BUY'
    assert engine.runtime.pending.status == 'PARTIALLY_FILLED'
    assert engine.runtime.pending.partial_executed_qty == 0.004
    assert engine.runtime.pending.remaining_qty == pytest.approx(0.006)
    assert str(engine.runtime.state).endswith('BUY_PENDING') or engine.runtime.state == 'BUY_PENDING'
    assert any(call[0] == 'RECOVERY_RECONCILE_COMPLETED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_startup_recovery_clears_orphan_local_pending_when_live_order_missing() -> None:
    engine = make_engine(open_orders=[])
    engine.runtime.pending = PendingOrder(side='BUY', price=2250.0, qty=0.01, order_id='local-only', client_order_id='local-cid')

    snapshot = await TradeBotEngine._startup_reconcile_persistent_state(engine)

    assert snapshot['pending_action'] == 'CLEARED_ORPHAN_LOCAL_PENDING'
    assert engine.runtime.pending is None
    assert str(engine.runtime.state).endswith('FLAT') or engine.runtime.state == 'FLAT'


@pytest.mark.asyncio
async def test_startup_recovery_rehydrates_position_from_live_balance() -> None:
    engine = make_engine(open_orders=[], base_free=0.0112)

    snapshot = await TradeBotEngine._startup_reconcile_persistent_state(engine)

    assert snapshot['position_action'] == 'REHYDRATED_FROM_LIVE_BALANCE'
    assert snapshot['has_position'] is True
    assert engine.runtime.position is not None
    assert engine.runtime.position.qty == 0.0112
    assert engine.runtime.position.source == 'startup_live_balance_rehydrate'
    assert str(engine.runtime.state).endswith('IN_POSITION') or engine.runtime.state == 'IN_POSITION'


@pytest.mark.asyncio
async def test_startup_recovery_clears_orphan_local_position_without_live_balance() -> None:
    engine = make_engine(open_orders=[], base_free=0.0)
    engine.runtime.position = Position(qty=0.0112, entry_price=2250.0, source='persisted')

    snapshot = await TradeBotEngine._startup_reconcile_persistent_state(engine)

    assert snapshot['position_action'] == 'CLEARED_ORPHAN_LOCAL_POSITION'
    assert engine.runtime.position is None
    assert str(engine.runtime.state).endswith('FLAT') or engine.runtime.state == 'FLAT'
