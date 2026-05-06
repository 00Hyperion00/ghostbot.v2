from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, Position, RuntimeState, SymbolRules


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
    def __init__(self) -> None:
        self.create_calls = 0

    async def create_limit_order(self, **kwargs):
        self.create_calls += 1
        return {'status': 'NEW', 'orderId': f'order-{self.create_calls}'}


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


@pytest.mark.asyncio
async def test_entry_guard_blocks_after_max_consecutive_losses() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.session.consecutive_losses = engine.settings.max_consecutive_losses

    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.runtime.pending is None
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'MAX_CONSECUTIVE_LOSSES_REACHED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_entry_guard_blocks_when_daily_loss_limit_reached() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.settings.max_daily_loss_pct = 1.0
    engine.runtime.balances['USDT'] = Balance(free=1000.0, locked=0.0, dust=0.0)
    engine.runtime.balances['ETH'] = Balance(free=0.0, locked=0.0, dust=0.0)
    engine.runtime.session.daily_realized_pnl = -15.0

    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.runtime.pending is None
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'DAILY_LOSS_LIMIT_REACHED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_exit_guard_blocks_min_notional_without_exception() -> None:
    engine = make_engine(state='IN_POSITION')
    engine.runtime.balances['ETH'] = Balance(free=0.0001, locked=0.0, dust=0.0)
    engine.runtime.position.qty = 0.0001

    await TradeBotEngine._submit_exit(engine, source='manual_force_sell')

    assert engine.exchange.create_calls == 0
    assert engine.runtime.pending is None
    assert any(call[0] == 'EXIT_BLOCKED' and call[2]['skipCode'] == 'MIN_NOTIONAL_BLOCKED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_entry_guard_blocks_insufficient_quote_balance_without_exception() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.balances['USDT'] = Balance(free=1.0, locked=0.0, dust=0.0)

    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.exchange.create_calls == 0
    assert engine.runtime.pending is None
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] in {'INSUFFICIENT_QUOTE_BALANCE', 'MIN_NOTIONAL_BLOCKED'} for call in engine.logger.warn_calls)



@pytest.mark.asyncio
async def test_entry_guard_clears_stale_position_from_cached_balances() -> None:
    engine = make_engine(state='IN_POSITION')
    engine.runtime.balances['ETH'] = Balance(free=0.0, locked=0.0, dust=0.0)
    engine.runtime.position = Position(qty=0.0108, entry_price=2315.0, source='manual_force_buy', order_id='entry-1')

    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.runtime.position is None
    assert engine.runtime.pending is not None
    assert any(call[0] == 'STALE_POSITION_CLEARED' for call in engine.logger.warn_calls)
    assert any(call[0] == 'ORDER_SUBMITTED' and call[2]['side'] == 'BUY' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_auto_safe_mode_enabled_after_consecutive_loss_kill_switch() -> None:
    engine = make_engine(state='IN_POSITION')
    engine.runtime.session.consecutive_losses = engine.settings.max_consecutive_losses - 1

    pending = type('PendingLike', (), {})()
    from tradebot.models import PendingOrder
    pending = PendingOrder(side='SELL', price=2310.0, qty=0.0108, order_id='exit-1', client_order_id='cid-1', source='manual_force_sell')

    await TradeBotEngine._finalize_exit_filled(engine, pending, source='live_order', fill_price=2300.0, fill_qty=0.0108)

    assert engine.runtime.safe_mode is True
    assert engine.runtime.safe_mode_until is not None
    assert any(call[0] == 'CONSECUTIVE_LOSS_LOCKED' for call in engine.logger.warn_calls)
    assert any(call[0] == 'SAFE_MODE_AUTO_ENABLED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_auto_safe_mode_enabled_after_daily_loss_limit_hit() -> None:
    engine = make_engine(state='IN_POSITION')
    engine.settings.max_daily_loss_pct = 1.0
    engine.runtime.balances['USDT'] = Balance(free=1000.0, locked=0.0, dust=0.0)
    engine.runtime.balances['ETH'] = Balance(free=0.0108, locked=0.0, dust=0.0)
    engine.runtime.session.daily_realized_pnl = -9.5

    from tradebot.models import PendingOrder
    pending = PendingOrder(side='SELL', price=2310.0, qty=0.0108, order_id='exit-1', client_order_id='cid-1', source='manual_force_sell')

    await TradeBotEngine._finalize_exit_filled(engine, pending, source='live_order', fill_price=2200.0, fill_qty=0.0108)

    assert engine.runtime.safe_mode is True
    assert any(call[0] == 'DAILY_LOSS_LOCKED' for call in engine.logger.warn_calls)
    assert any(call[0] == 'SAFE_MODE_AUTO_ENABLED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_risk_reset_clears_auto_safe_mode() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.safe_mode = True
    engine.runtime.safe_mode_until = 123456789

    await TradeBotEngine.risk_reset(engine)

    assert engine.runtime.safe_mode is False
    assert engine.runtime.safe_mode_until is None
    assert any(call[0] == 'SAFE_MODE_AUTO_CLEARED' for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_entry_guard_returns_daily_loss_reason_even_when_safe_mode_auto_enabled() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.balances['USDT'] = Balance(free=1000.0, locked=0.0, dust=0.0)
    engine.runtime.balances['ETH'] = Balance(free=0.0, locked=0.0, dust=0.0)
    engine.runtime.session.daily_realized_pnl = -20.0

    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.runtime.pending is None
    assert engine.runtime.safe_mode is True
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'DAILY_LOSS_LIMIT_REACHED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_manual_safe_mode_blocks_entry_with_safe_mode_locked() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None

    await TradeBotEngine.toggle_safe_mode(engine)
    await TradeBotEngine._submit_entry(engine, source='manual_force_buy')

    assert engine.runtime.safe_mode is True
    assert engine.runtime.safe_mode_source == 'manual'
    assert engine.runtime.pending is None
    assert any(call[0] == 'SAFE_MODE_MANUAL_ENABLED' for call in engine.logger.info_calls)
    assert any(call[0] == 'ENTRY_BLOCKED' and call[2]['skipCode'] == 'SAFE_MODE_LOCKED' for call in engine.logger.warn_calls)


@pytest.mark.asyncio
async def test_manual_safe_mode_does_not_block_exit() -> None:
    engine = make_engine(state='IN_POSITION')

    await TradeBotEngine.toggle_safe_mode(engine)
    await TradeBotEngine._submit_exit(engine, source='manual_force_sell')

    assert engine.runtime.safe_mode is True
    assert engine.runtime.safe_mode_source == 'manual'
    assert engine.runtime.pending is not None
    assert engine.runtime.pending.side == 'SELL'
    assert engine.exchange.create_calls == 1


@pytest.mark.asyncio
async def test_risk_reset_preserves_manual_safe_mode() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    await TradeBotEngine.toggle_safe_mode(engine)

    await TradeBotEngine.risk_reset(engine)

    assert engine.runtime.safe_mode is True
    assert engine.runtime.safe_mode_source == 'manual'
    assert any(call[0] == 'RISK_STATS_RESET' and call[2]['safeModeCleared'] is False for call in engine.logger.info_calls)


@pytest.mark.asyncio
async def test_auto_safe_mode_expires_and_status_reports_remaining_seconds() -> None:
    engine = make_engine(state='FLAT')
    engine.runtime.position = None
    engine.runtime.safe_mode = True
    engine.runtime.safe_mode_source = 'daily_loss'
    engine.runtime.safe_mode_reason_code = 'DAILY_LOSS_LIMIT_REACHED'
    from tradebot.engine import utc_ms
    engine.runtime.safe_mode_until = utc_ms() - 1

    status = await TradeBotEngine.get_status(engine)

    assert engine.runtime.safe_mode is False
    assert engine.runtime.safe_mode_source is None
    assert status['safe_mode'] is False
    assert status['safe_mode_remaining_sec'] is None
    assert any(call[0] == 'SAFE_MODE_AUTO_EXPIRED' for call in engine.logger.info_calls)
