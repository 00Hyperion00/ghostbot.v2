from __future__ import annotations

import asyncio
from types import SimpleNamespace

from tradebot.decision_audit import build_decision_audit_snapshot, empty_decision_audit_snapshot
from tradebot.engine import TradeBotEngine
from tradebot.models import RuntimeState, SignalDecision
from tradebot.config import Settings


class DummyLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.calls.append((code, message, data))


def make_settings(**overrides):
    defaults = {
        'symbol': 'ETHUSDT',
        'kline_interval': '1m',
        'ai_provider_enabled': True,
        'ai_provider_mode': 'local_xgboost',
        'ai_buy_threshold': 0.64,
        'ai_sell_threshold': 0.57,
        'ai_hold_band_low': 0.45,
        'ai_hold_band_high': 0.55,
        'ai_indecision_margin': 0.08,
        'auto_trade_on_signal': True,
        'auto_trade_signal_mode': 'normal',
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_decision(signal: str = 'BUY') -> SignalDecision:
    return SignalDecision(
        signal=signal,
        trend='UP',
        reason='AI Kararı | Güven Skoru: %72.0',
        provider='ai',
        confidence=0.72,
        last_evaluated_close_time=123456,
        metrics={
            'technicalSignal': 'HOLD',
            'technicalTrend': 'UP',
            'technicalReason': 'Trend UP | RSI 55.00',
            'emaFast': 101.0,
            'emaSlow': 100.0,
            'rsi': 55.0,
            'atr': 1.25,
            'volumeRatio': 1.2,
            'takerBuyPressure': 0.6,
            'buyProbability': 0.72,
            'sellProbability': 0.12,
            'holdProbability': 0.16,
            'rawMargin': 0.56,
            'rawPredictedClass': 1,
            'calibratedClass': 1,
            'calibrationReason': 'ACCEPT_HIGH_CONFIDENCE',
        },
    )


def test_decision_audit_snapshot_explains_thresholds_and_technical_metrics() -> None:
    settings = make_settings()
    runtime = RuntimeState(state='FLAT')
    technical = SignalDecision(signal='HOLD', trend='UP', reason='Trend UP', provider='technical')
    decision = make_decision('BUY')

    snapshot = build_decision_audit_snapshot(
        now=1000,
        symbol='ETHUSDT',
        interval='1m',
        settings=settings,
        runtime=runtime,
        technical_decision=technical,
        model_decision=decision,
        effective_decision=decision,
        signal_key='ETHUSDT|1m|BUY|123456|abc',
        action='ORDER_SUBMISSION_PLANNED',
        should_submit_order=True,
    )

    assert snapshot['contract_version'] == '4B.4.3.6.6.19'
    assert snapshot['raw_decision']['signal'] == 'BUY'
    assert snapshot['effective_decision']['signal'] == 'BUY'
    assert snapshot['threshold_trace']['buy_threshold'] == 0.64
    assert snapshot['threshold_trace']['calibration_reason'] == 'ACCEPT_HIGH_CONFIDENCE'
    assert snapshot['technical']['metrics']['rsi'] == 55.0
    assert snapshot['ai']['buy_probability'] == 0.72
    assert snapshot['guard_path']['action_intent'] == 'ENTRY'
    assert snapshot['should_submit_order'] is True
    assert 'ORDER_SUBMISSION_INTENDED' in snapshot['reason_codes']


def test_decision_audit_hold_snapshot_is_non_blocking() -> None:
    settings = make_settings()
    runtime = RuntimeState(state='FLAT')
    technical = SignalDecision(signal='HOLD', trend='UNKNOWN', reason='Yetersiz veri', provider='technical')
    decision = SignalDecision(signal='HOLD', trend='UNKNOWN', reason='AI Kararı | Güven Skoru: %44.0', provider='ai', confidence=0.44, metrics={'calibrationReason': 'REJECT_LOW_MARGIN'})

    snapshot = build_decision_audit_snapshot(
        now=1000,
        symbol='ETHUSDT',
        interval='1m',
        settings=settings,
        runtime=runtime,
        technical_decision=technical,
        model_decision=decision,
        effective_decision=decision,
        signal_key='key',
        action='AUTO_TRADE_SKIP',
        should_submit_order=False,
        skip_code='NO_ACTION_SIGNAL_HOLD',
    )

    assert snapshot['effective_decision']['signal'] == 'HOLD'
    assert snapshot['guard_path']['skip_code'] == 'NO_ACTION_SIGNAL_HOLD'
    assert snapshot['should_submit_order'] is False
    assert 'RAW_SIGNAL_HOLD' in snapshot['reason_codes']
    assert 'REJECT_LOW_MARGIN' in snapshot['reason_codes']


def test_engine_records_decision_audit_snapshot_and_event() -> None:
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.settings = make_settings()
    engine.runtime = RuntimeState(state='FLAT')
    engine.logger = DummyLogger()
    technical = SignalDecision(signal='HOLD', trend='UP', reason='Trend UP', provider='technical')
    decision = make_decision('BUY')

    snapshot = TradeBotEngine._record_decision_audit(
        engine,
        technical=technical,
        decision=decision,
        effective=decision,
        signal_key='sig-key',
        action='ORDER_SUBMISSION_PLANNED',
        should_submit_order=True,
    )

    assert engine.runtime.decision_audit_snapshot == snapshot
    assert snapshot['signal_key'] == 'sig-key'
    assert snapshot['action_intent'] == 'ENTRY'
    assert any(call[0] == 'STRATEGY_DECISION_AUDIT' for call in engine.logger.calls)


def test_engine_status_includes_decision_audit_snapshot_contract() -> None:
    engine = TradeBotEngine.__new__(TradeBotEngine)
    engine.settings = Settings(ai_provider_enabled=False)
    engine.runtime = RuntimeState()
    engine._running = True
    engine.store = None
    engine.ai_provider = None
    engine.symbol_rules = None
    engine._latest_book = {}
    engine._closed_candles = []
    engine._expire_safe_mode = lambda: None
    engine._health_snapshot = lambda: {'account_consistency': 'HEALTHY', 'position_consistency': 'HEALTHY', 'pending_consistency': 'HEALTHY'}
    engine._risk_snapshot = lambda: {}
    engine._ai_snapshot = lambda: {}
    engine._pending_snapshot = lambda: {}
    engine._position_snapshot = lambda runtime_payload: {}
    engine._event_audit_snapshot = lambda: {}
    engine._model_quality_snapshot = lambda: {}
    engine._performance_snapshot = lambda: {}
    engine._config_safety_snapshot = lambda: {}
    engine._diagnostics_snapshot = lambda status: {}
    engine._reconciliation_snapshot = lambda: {}

    status = asyncio.run(TradeBotEngine.get_status(engine))

    assert status['contract_version'] == '4B.4.3.6.6.20'
    assert status['decision_audit_snapshot']['contract_version'] == '4B.4.3.6.6.19'
    assert status['decision_audit_snapshot']['action'] == 'NO_DATA'


def test_empty_decision_audit_snapshot_shape() -> None:
    snapshot = empty_decision_audit_snapshot(now=42, symbol='ETHUSDT', interval='1m')
    assert snapshot['contract_version'] == '4B.4.3.6.6.19'
    assert snapshot['reason_codes'] == ['NO_DECISION_YET']
    assert snapshot['guard_path']['should_submit_order'] is False
