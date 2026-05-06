from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from tradebot.engine import TradeBotEngine
from tradebot.enums import BotState
from tradebot.models import Balance, PendingOrder, Position, RuntimeState, SessionStats
from tradebot.utils import utc_ms


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, str, dict]] = []
        self.warn_calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))


def make_engine(runtime: RuntimeState | None = None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.runtime = runtime or RuntimeState(state=BotState.FLAT.value, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.logger = DummyLogger()
    engine.settings = SimpleNamespace(
        symbol='ETHUSDT',
        ai_provider_enabled=True,
        ai_provider_mode='local_xgboost',
        ai_model_path='models/ETHUSDT_model_4b43664.ubj',
        ai_confidence_threshold=0.6,
        max_daily_trades=0,
        max_consecutive_losses=3,
        max_daily_loss_pct=2.0,
    )
    engine.ai_provider = SimpleNamespace(
        available=True,
        load_error=None,
        schema_validated=True,
        schema_version='4B.3.4',
        feature_pack_name='core_price_action_regime_vwap_mtf15_v1',
        feature_count=37,
        feature_lag=1,
        threshold_config=lambda: {},
    )
    engine._running = True
    engine._latest_book = {}
    engine._closed_candles = []
    engine.symbol_rules = None
    engine._save_runtime = lambda: None
    return engine


def stale_runtime() -> RuntimeState:
    runtime = RuntimeState(state=BotState.FLAT.value, ws_status='CONNECTED', symbol='ETHUSDT')
    runtime.pending = None
    runtime.position = None
    runtime.session = SessionStats(
        day_key='2026-04-27',
        daily_realized_pnl=0.031,
        daily_trade_count=2,
        consecutive_losses=1,
        last_closed_pnl=-0.01,
    )
    runtime.last_signal = 'BUY'
    runtime.signal_reason = 'AI Kararı | Güven Skoru: %71.2'
    runtime.trend = 'UP'
    runtime.last_signal_provider = 'local_xgboost'
    runtime.last_signal_confidence = 0.712
    runtime.last_signal_metrics = {'schemaValidated': True, 'buyProbability': 0.712}
    runtime.last_evaluated_close_time = 1777488659999
    runtime.last_signal_key = 'ETHUSDT|1m|BUY|old'
    runtime.auto_debug = 'AUTO_ENTRY_ACCEPTED | old'
    runtime.auto_guard = 'SELL_PENDING | key=old | 23:47:03'
    runtime.live_order_status = 'FILLED'
    runtime.last_preflight = 'OK | EXIT | LIVE_DEMO | 27.04.2026 23:47:03'
    runtime.last_order_event = 'SELL filled @ 2291.31'
    runtime.last_reconcile_result = 'ORPHAN_PENDING'
    runtime.active_anomaly_code = 'PENDING_STATE_WITHOUT_ORDER'
    runtime.entry_lock_until = utc_ms() - 1_000
    return runtime


def test_startup_hygiene_clears_stale_flat_telemetry_without_active_exposure() -> None:
    runtime = stale_runtime()
    engine = make_engine(runtime)

    snapshot = TradeBotEngine._apply_startup_hygiene(engine)

    assert snapshot['cleaned_count'] > 0
    assert 'session_day_rollover' in snapshot['cleaned']
    assert 'auto_guard' in snapshot['cleaned']
    assert 'last_preflight' in snapshot['cleaned']
    assert 'last_order_event' in snapshot['cleaned']
    assert 'stale_signal' in snapshot['cleaned']
    assert runtime.session.day_key == datetime.now(timezone.utc).strftime('%Y-%m-%d')
    assert runtime.session.daily_realized_pnl == 0.0
    assert runtime.session.daily_trade_count == 0
    assert runtime.session.consecutive_losses == 0
    assert runtime.session.last_closed_pnl == 0.0
    assert runtime.last_signal == 'HOLD'
    assert runtime.last_signal_confidence is None
    assert runtime.last_signal_metrics == {}
    assert runtime.auto_guard == '-'
    assert runtime.last_preflight == '-'
    assert runtime.last_order_event == 'Henüz emir yok'
    assert runtime.entry_lock_until is None
    assert runtime.active_anomaly_code is None
    assert runtime.startup_hygiene == snapshot
    assert any(call[0] == 'STARTUP_HYGIENE_APPLIED' for call in engine.logger.info_calls)


def test_startup_hygiene_preserves_active_pending_telemetry() -> None:
    runtime = stale_runtime()
    runtime.state = BotState.BUY_PENDING.value
    runtime.pending = PendingOrder(
        side='BUY',
        price=2225.0,
        qty=0.01,
        status='NEW',
        order_id='123',
        client_order_id='cid',
        submitted_at=utc_ms(),
    )
    engine = make_engine(runtime)

    snapshot = TradeBotEngine._apply_startup_hygiene(engine)

    assert snapshot['has_pending'] is True
    assert runtime.state == BotState.BUY_PENDING.value
    assert runtime.pending is not None
    assert runtime.auto_guard == 'SELL_PENDING | key=old | 23:47:03'
    assert runtime.last_preflight == 'OK | EXIT | LIVE_DEMO | 27.04.2026 23:47:03'
    assert runtime.last_order_event == 'SELL filled @ 2291.31'


def test_startup_hygiene_preserves_active_position_order_context() -> None:
    runtime = stale_runtime()
    runtime.position = Position(qty=0.01, entry_price=2220.0, source='live_balance_rehydrate')
    runtime.state = BotState.IN_POSITION.value
    runtime.balances = {'ETH': Balance(free=0.01, locked=0.0, dust=0.0)}
    engine = make_engine(runtime)

    snapshot = TradeBotEngine._apply_startup_hygiene(engine)

    assert snapshot['has_position'] is True
    assert runtime.position is not None
    assert runtime.state == BotState.IN_POSITION.value
    assert runtime.last_order_event == 'SELL filled @ 2291.31'
    assert runtime.auto_guard == 'SELL_PENDING | key=old | 23:47:03'


def test_startup_hygiene_repairs_pending_state_without_pending_order() -> None:
    runtime = stale_runtime()
    runtime.state = BotState.SELL_PENDING.value
    runtime.pending = None
    runtime.position = None
    engine = make_engine(runtime)

    snapshot = TradeBotEngine._apply_startup_hygiene(engine)

    assert runtime.state == BotState.FLAT.value
    assert 'stale_state:SELL_PENDING' in snapshot['cleaned']


@pytest.mark.asyncio
async def test_status_exposes_startup_hygiene_snapshot_and_43666_contract() -> None:
    runtime = stale_runtime()
    engine = make_engine(runtime)
    TradeBotEngine._apply_startup_hygiene(engine)

    status = await TradeBotEngine.get_status(engine)

    assert status['contract_version'] == '4B.4.3.6.6.6'
    assert 'startup_hygiene_snapshot' in status
    assert status['startup_hygiene_snapshot']['cleaned_count'] > 0
    assert status['startup_hygiene_snapshot']['has_pending'] is False
    assert status['startup_hygiene_snapshot']['has_position'] is False
