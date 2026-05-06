from __future__ import annotations

from dataclasses import dataclass

import pytest

from tradebot.engine import TradeBotEngine, utc_ms
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


class SequencedExchange:
    def __init__(self, *, fetch_order_results=None, cancel_exc: Exception | None = None) -> None:
        self.fetch_order_results = list(fetch_order_results or [])
        self.cancel_exc = cancel_exc
        self.cancel_calls = 0

    async def fetch_order(self, symbol: str, order_id=None, client_order_id=None):
        if self.fetch_order_results:
            result = self.fetch_order_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return None

    async def cancel_order(self, **kwargs):
        self.cancel_calls += 1
        if self.cancel_exc is not None:
            raise self.cancel_exc
        return {'ok': True}

    async def fetch_open_orders(self, symbol: str):
        return []

    async def create_limit_order(self, **kwargs):
        return {'status': 'NEW', 'orderId': 'created-1'}


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


def make_engine(*, state: str = 'BUY_PENDING', pending: PendingOrder | None = None, position: Position | None = None, exchange: SequencedExchange | None = None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = exchange or SequencedExchange()
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.session.day_key = '2026-04-21'
    engine.runtime.balances = {
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
        'ETH': Balance(free=0.0, locked=0.0, dust=0.0),
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
    engine._closed_candles = [candle] * 20
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
async def test_cancel_pending_suppresses_duplicate_request() -> None:
    pending = PendingOrder(side='BUY', price=2315.0, qty=0.0107, status='CANCEL_REQUESTED', order_id='oid-1', client_order_id='cid-1', cancel_requested=True, remaining_qty=0.0107)
    exchange = SequencedExchange()
    engine = make_engine(pending=pending, exchange=exchange)

    await TradeBotEngine.cancel_pending(engine)

    assert exchange.cancel_calls == 0
    assert any(call[0] == 'ORDER_CANCEL_SUPPRESSED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_cancel_pending_resolves_filled_race_without_warning() -> None:
    pending = PendingOrder(side='BUY', price=2320.0, qty=0.0107, status='NEW', order_id='oid-1', client_order_id='cid-1', remaining_qty=0.0107)
    exchange = SequencedExchange(
        fetch_order_results=[
            {'status': 'NEW', 'executedQty': '0.0', 'origQty': '0.0107', 'price': '2320.0'},
            {'status': 'FILLED', 'executedQty': '0.0107', 'origQty': '0.0107', 'price': '2320.0'},
        ],
        cancel_exc=RuntimeError("Client error '400 Bad Request' for url 'https://demo-api.binance.com/api/v3/order'")
    )
    engine = make_engine(pending=pending, exchange=exchange)

    await TradeBotEngine.cancel_pending(engine)

    assert exchange.cancel_calls == 1
    assert engine.runtime.pending is None
    assert engine.runtime.position is not None
    assert engine.runtime.state == 'IN_POSITION'
    assert any(call[0] == 'ORDER_CANCEL_RACE_FILLED' for call in engine.logger.info_calls)
    assert not any(call[0] == 'ORDER_CANCEL_WARN' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_auto_safe_mode_expiry_with_missing_source_cleans_without_log() -> None:
    engine = make_engine(state='FLAT', pending=None)
    engine.runtime.safe_mode = True
    engine.runtime.safe_mode_until = utc_ms() - 1
    engine.runtime.safe_mode_source = None
    engine.runtime.safe_mode_reason_code = None

    status = await TradeBotEngine.get_status(engine)

    assert engine.runtime.safe_mode is False
    assert status['safe_mode'] is False
    assert not any(call[0] == 'SAFE_MODE_AUTO_EXPIRED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_same_kill_switch_does_not_log_duplicate_enable_events() -> None:
    engine = make_engine(state='FLAT', pending=None)
    engine.runtime.session.consecutive_losses = engine.settings.max_consecutive_losses

    TradeBotEngine._refresh_risk_kill_switch(engine, reason='ENTRY_GUARD')
    first_until = engine.runtime.safe_mode_until
    TradeBotEngine._refresh_risk_kill_switch(engine, reason='ENTRY_GUARD')

    assert engine.runtime.safe_mode is True
    assert engine.runtime.safe_mode_until == first_until
    assert sum(1 for call in engine.logger.warn_calls if call[0] == 'CONSECUTIVE_LOSS_LOCKED') == 1
    assert sum(1 for call in engine.logger.warn_calls if call[0] == 'SAFE_MODE_AUTO_ENABLED') == 1


@pytest.mark.asyncio
async def test_status_exposes_consistency_fields() -> None:
    position = Position(qty=0.0107, entry_price=2320.0, source='manual_force_buy')
    engine = make_engine(state='IN_POSITION', pending=None, position=position)
    engine.runtime.balances['ETH'] = Balance(free=0.0, locked=0.0, dust=0.0)

    status = await TradeBotEngine.get_status(engine)

    assert status['account_consistency'] == 'WARNING'
    assert status['position_consistency'] == 'WARNING'
    assert status['active_anomaly_code'] == 'BALANCE_POSITION_MISMATCH'
    assert 'kill_switch_active' in status
