from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time

from tradebot.engine import TradeBotEngine
from tradebot.model_quality import (
    ModelQualityConfig,
    ModelQualityMonitor,
    build_model_quality_snapshot,
    build_quality_sample,
    should_emit_quality_event,
)
from tradebot.models import RuntimeState, SignalDecision


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
    ai_model_path: str = 'models/ETHUSDT_model.ubj'
    model_quality_enabled: bool = True
    model_quality_window_size: int = 20
    model_quality_min_samples: int = 5
    model_quality_hold_warning_pct: float = 80.0
    model_quality_hold_critical_pct: float = 90.0
    model_quality_avg_conf_warning: float = 0.50
    model_quality_avg_conf_critical: float = 0.42
    model_quality_low_margin_warning_pct: float = 35.0
    model_quality_low_margin_critical_pct: float = 55.0
    model_quality_stale_warning_days: int = 14
    model_quality_stale_critical_days: int = 30


class DummyLogger:
    def __init__(self) -> None:
        self.warn_calls: list[tuple[str, str, dict]] = []
        self.info_calls: list[tuple[str, str, dict]] = []

    def warn(self, code: str, message: str, data: dict | None = None, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data or {}))

    def info(self, code: str, message: str, data: dict | None = None, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data or {}))


def _decision(signal: str, confidence: float, calibration: str = 'RAW_TOP_HOLD') -> SignalDecision:
    return SignalDecision(
        signal=signal,
        trend='UP',
        reason='test',
        provider='ai',
        confidence=confidence,
        metrics={
            'calibrationReason': calibration,
            'buyProbability': 0.2,
            'sellProbability': 0.1,
            'holdProbability': 0.7,
            'rawPredictedClass': 0,
            'calibratedClass': {'HOLD': 0, 'BUY': 1, 'SELL': 2}[signal],
            'featureCount': 37,
            'featureLag': 1,
            'schemaVersion': '4B.3.4',
            'featurePackName': 'core_price_action_regime_vwap_mtf15_v1',
        },
        last_evaluated_close_time=123,
    )


def test_model_quality_collects_prediction_distribution() -> None:
    cfg = ModelQualityConfig(min_samples=1, window_size=10)
    monitor = ModelQualityMonitor(cfg)
    for signal in ['BUY', 'SELL', 'HOLD', 'HOLD']:
        monitor.add_sample(build_quality_sample(_decision(signal, 0.61), symbol='ETHUSDT'))

    snap = monitor.snapshot()

    assert snap['sample_count'] == 4
    assert snap['prediction_distribution'] == {'BUY': 1, 'SELL': 1, 'HOLD': 2}
    assert snap['prediction_distribution_pct']['HOLD'] == 50.0
    assert snap['confidence']['avg'] == 0.61


def test_model_quality_flags_hold_dominance_and_low_confidence() -> None:
    cfg = ModelQualityConfig(min_samples=5, hold_warning_pct=80.0, hold_critical_pct=101.0, avg_conf_warning=0.50, avg_conf_critical=0.0)
    samples = [build_quality_sample(_decision('HOLD', 0.43), symbol='ETHUSDT') for _ in range(5)]

    snap = build_model_quality_snapshot(samples, cfg)

    assert snap['severity'] == 'warning'
    assert 'HOLD_DOMINANCE_HIGH' in snap['reason_codes']
    assert 'AVG_CONFIDENCE_LOW' in snap['reason_codes']
    assert snap['recommendation'] == 'MONITOR_OR_RETRAIN'


def test_model_quality_flags_low_margin_rejection() -> None:
    cfg = ModelQualityConfig(min_samples=5, low_margin_warning_pct=35.0)
    samples = [build_quality_sample(_decision('HOLD', 0.55, 'REJECT_LOW_MARGIN'), symbol='ETHUSDT') for _ in range(5)]

    snap = build_model_quality_snapshot(samples, cfg)

    assert snap['calibration']['reject_low_margin_pct'] == 100.0
    assert 'LOW_MARGIN_REJECTION_CRITICAL' in snap['reason_codes'] or 'LOW_MARGIN_REJECTION_HIGH' in snap['reason_codes']


def test_model_quality_recommends_retrain_for_stale_model(tmp_path: Path) -> None:
    model = tmp_path / 'model.ubj'
    model.write_text('x', encoding='utf-8')
    old = time.time() - 31 * 86400
    os.utime(model, (old, old))
    cfg = ModelQualityConfig(min_samples=1, stale_critical_days=30)
    samples = [build_quality_sample(_decision('BUY', 0.72), symbol='ETHUSDT', model_path=str(model))]

    snap = build_model_quality_snapshot(samples, cfg)

    assert snap['severity'] == 'critical'
    assert snap['recommendation'] == 'RETRAIN_RECOMMENDED'
    assert 'MODEL_STALE_CRITICAL' in snap['reason_codes']


def test_should_emit_quality_event_only_on_state_change() -> None:
    prev = {'severity': 'warning', 'recommendation': 'MONITOR_OR_RETRAIN', 'reason_codes': ['A']}
    same = {'severity': 'warning', 'recommendation': 'MONITOR_OR_RETRAIN', 'reason_codes': ['A']}
    changed = {'severity': 'healthy', 'recommendation': 'OK', 'reason_codes': []}

    assert should_emit_quality_event(prev, same) is False
    assert should_emit_quality_event(prev, changed) is True


def test_engine_records_model_quality_without_overriding_signal() -> None:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.runtime = RuntimeState()
    engine.logger = DummyLogger()
    engine.model_quality_monitor = ModelQualityMonitor(ModelQualityConfig(min_samples=1, window_size=10))

    decision = _decision('BUY', 0.77)
    snap = TradeBotEngine._record_model_quality_sample(engine, decision)

    assert decision.signal == 'BUY'
    assert snap is not None
    assert engine.runtime.model_quality_snapshot is not None
    assert engine.runtime.model_quality_snapshot['sample_count'] == 1
    assert engine.runtime.model_quality_snapshot['prediction_distribution']['BUY'] == 1


def test_model_quality_disabled_snapshot_is_non_blocking() -> None:
    engine = object.__new__(TradeBotEngine)
    settings = DummySettings()
    settings.model_quality_enabled = False
    engine.settings = settings
    engine.runtime = RuntimeState()
    engine.logger = DummyLogger()

    snap = TradeBotEngine._record_model_quality_sample(engine, _decision('SELL', 0.7))

    assert snap['enabled'] is False
    assert snap['severity'] == 'disabled'
