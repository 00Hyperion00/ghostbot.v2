from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from time import time
from typing import Any, Iterable

from .models import SignalDecision


MODEL_QUALITY_CONTRACT_VERSION = "4B.4.3.6.6.13"


@dataclass(slots=True)
class ModelQualityConfig:
    enabled: bool = True
    window_size: int = 200
    min_samples: int = 30
    hold_warning_pct: float = 80.0
    hold_critical_pct: float = 90.0
    avg_conf_warning: float = 0.50
    avg_conf_critical: float = 0.42
    low_margin_warning_pct: float = 35.0
    low_margin_critical_pct: float = 55.0
    stale_warning_days: int = 14
    stale_critical_days: int = 30


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pct(part: int | float, total: int | float) -> float:
    if not total:
        return 0.0
    return round((float(part) / float(total)) * 100.0, 4)


def config_from_settings(settings: Any) -> ModelQualityConfig:
    return ModelQualityConfig(
        enabled=bool(getattr(settings, "model_quality_enabled", True)),
        window_size=int(getattr(settings, "model_quality_window_size", 200) or 200),
        min_samples=int(getattr(settings, "model_quality_min_samples", 30) or 30),
        hold_warning_pct=float(getattr(settings, "model_quality_hold_warning_pct", 80.0) or 80.0),
        hold_critical_pct=float(getattr(settings, "model_quality_hold_critical_pct", 90.0) or 90.0),
        avg_conf_warning=float(getattr(settings, "model_quality_avg_conf_warning", 0.50) or 0.50),
        avg_conf_critical=float(getattr(settings, "model_quality_avg_conf_critical", 0.42) or 0.42),
        low_margin_warning_pct=float(getattr(settings, "model_quality_low_margin_warning_pct", 35.0) or 35.0),
        low_margin_critical_pct=float(getattr(settings, "model_quality_low_margin_critical_pct", 55.0) or 55.0),
        stale_warning_days=int(getattr(settings, "model_quality_stale_warning_days", 14) or 14),
        stale_critical_days=int(getattr(settings, "model_quality_stale_critical_days", 30) or 30),
    )


def build_quality_sample(
    decision: SignalDecision,
    *,
    symbol: str,
    model_path: str | None = None,
    schema_version: str | None = None,
    feature_pack_name: str | None = None,
    ts: int | None = None,
) -> dict[str, Any]:
    metrics = decision.metrics or {}
    calibration_reason = (
        metrics.get("calibrationReason")
        or metrics.get("calibration_reason")
        or metrics.get("calibration")
    )
    return {
        "ts": int(ts or time() * 1000),
        "symbol": symbol,
        "signal": str(decision.signal or "HOLD").upper(),
        "confidence": _safe_float(decision.confidence),
        "provider": decision.provider,
        "trend": decision.trend,
        "reason": decision.reason,
        "raw_predicted_class": _safe_int(metrics.get("rawPredictedClass")),
        "calibrated_class": _safe_int(metrics.get("calibratedClass")),
        "calibration_reason": str(calibration_reason) if calibration_reason is not None else None,
        "buy_probability": _safe_float(metrics.get("buyProbability")),
        "sell_probability": _safe_float(metrics.get("sellProbability")),
        "hold_probability": _safe_float(metrics.get("holdProbability")),
        "raw_top_probability": _safe_float(metrics.get("rawTopProbability")),
        "raw_margin": _safe_float(metrics.get("rawMargin")),
        "feature_count": _safe_int(metrics.get("featureCount")),
        "feature_lag": _safe_int(metrics.get("featureLag")),
        "schema_version": schema_version or metrics.get("schemaVersion"),
        "feature_pack_name": feature_pack_name or metrics.get("featurePackName"),
        "last_evaluated_close_time": decision.last_evaluated_close_time,
        "model_path": model_path,
    }


def _model_age_days(model_path: str | None) -> float | None:
    if not model_path:
        return None
    try:
        path = Path(model_path)
        if not path.exists():
            return None
        return round((time() - path.stat().st_mtime) / 86400.0, 4)
    except OSError:
        return None


class ModelQualityMonitor:
    def __init__(self, config: ModelQualityConfig | None = None) -> None:
        self.config = config or ModelQualityConfig()
        self.samples: deque[dict[str, Any]] = deque(maxlen=max(int(self.config.window_size or 1), 1))

    def add_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        self.samples.append(dict(sample))
        return self.snapshot()

    def snapshot(self, *, model_path: str | None = None) -> dict[str, Any]:
        return build_model_quality_snapshot(self.samples, self.config, model_path=model_path)


def build_model_quality_snapshot(
    samples: Iterable[dict[str, Any]],
    config: ModelQualityConfig | None = None,
    *,
    model_path: str | None = None,
) -> dict[str, Any]:
    cfg = config or ModelQualityConfig()
    items = [dict(item) for item in samples][-max(int(cfg.window_size or 1), 1):]
    sample_count = len(items)
    signals = [str(item.get("signal") or "HOLD").upper() for item in items]
    signal_counts = Counter(signals)
    prediction_distribution = {key: int(signal_counts.get(key, 0)) for key in ["BUY", "SELL", "HOLD"]}
    prediction_distribution_pct = {key: _pct(value, sample_count) for key, value in prediction_distribution.items()}

    confidence_values = [
        float(value)
        for value in (item.get("confidence") for item in items)
        if value is not None
    ]
    confidence = {
        "avg": round(mean(confidence_values), 6) if confidence_values else None,
        "min": round(min(confidence_values), 6) if confidence_values else None,
        "max": round(max(confidence_values), 6) if confidence_values else None,
        "last": round(confidence_values[-1], 6) if confidence_values else None,
    }

    calibration_reasons = [str(item.get("calibration_reason") or "").upper() for item in items]
    low_margin_count = sum(1 for reason in calibration_reasons if "LOW_MARGIN" in reason or "INDECISION" in reason)
    indecision_count = sum(1 for reason in calibration_reasons if "INDECISION" in reason)
    calibration = {
        "reject_low_margin_count": low_margin_count,
        "reject_low_margin_pct": _pct(low_margin_count, sample_count),
        "indecision_count": indecision_count,
        "indecision_pct": _pct(indecision_count, sample_count),
    }

    reason_codes: list[str] = []
    critical_reasons: list[str] = []
    enough = sample_count >= int(cfg.min_samples or 0)

    hold_pct = prediction_distribution_pct["HOLD"]
    actionable_pct = round(100.0 - hold_pct, 4)
    avg_conf = confidence["avg"]
    low_margin_pct = calibration["reject_low_margin_pct"]

    if enough and hold_pct >= cfg.hold_critical_pct:
        critical_reasons.append("HOLD_DOMINANCE_CRITICAL")
    elif enough and hold_pct >= cfg.hold_warning_pct:
        reason_codes.append("HOLD_DOMINANCE_HIGH")

    if enough and avg_conf is not None and avg_conf < cfg.avg_conf_critical:
        critical_reasons.append("AVG_CONFIDENCE_CRITICAL")
    elif enough and avg_conf is not None and avg_conf < cfg.avg_conf_warning:
        reason_codes.append("AVG_CONFIDENCE_LOW")

    if enough and low_margin_pct >= cfg.low_margin_critical_pct:
        critical_reasons.append("LOW_MARGIN_REJECTION_CRITICAL")
    elif enough and low_margin_pct >= cfg.low_margin_warning_pct:
        reason_codes.append("LOW_MARGIN_REJECTION_HIGH")

    if enough and actionable_pct < 10.0:
        reason_codes.append("ACTIONABLE_SIGNAL_LOW")

    age_days = _model_age_days(model_path or (items[-1].get("model_path") if items else None))
    if age_days is not None:
        if age_days >= cfg.stale_critical_days:
            critical_reasons.append("MODEL_STALE_CRITICAL")
        elif age_days >= cfg.stale_warning_days:
            reason_codes.append("MODEL_STALE_WARNING")

    reason_codes = critical_reasons + reason_codes
    severity = "critical" if critical_reasons else ("warning" if reason_codes else "healthy")
    if sample_count < int(cfg.min_samples or 0):
        severity = "warming_up" if sample_count else "no_data"
    recommendation = "RETRAIN_RECOMMENDED" if severity == "critical" else ("MONITOR_OR_RETRAIN" if severity == "warning" else "OK")

    latest = items[-1] if items else {}
    feature_sanity = {
        "feature_count": latest.get("feature_count"),
        "feature_lag": latest.get("feature_lag"),
        "schema_version": latest.get("schema_version"),
        "feature_pack_name": latest.get("feature_pack_name"),
        "missing_feature_count": latest.get("feature_count") is None if latest else False,
    }

    return {
        "contract_version": MODEL_QUALITY_CONTRACT_VERSION,
        "enabled": bool(cfg.enabled),
        "window_size": int(cfg.window_size),
        "sample_count": sample_count,
        "last_updated_at": items[-1].get("ts") if items else None,
        "model_path": model_path or latest.get("model_path"),
        "schema_version": latest.get("schema_version"),
        "feature_pack_name": latest.get("feature_pack_name"),
        "prediction_distribution": prediction_distribution,
        "prediction_distribution_pct": prediction_distribution_pct,
        "confidence": confidence,
        "calibration": calibration,
        "feature_sanity": feature_sanity,
        "model_age_days": age_days,
        "drift_flags": {
            "hold_dominance": any(code.startswith("HOLD_DOMINANCE") for code in reason_codes),
            "low_confidence": any(code.startswith("AVG_CONFIDENCE") for code in reason_codes),
            "class_imbalance": "ACTIONABLE_SIGNAL_LOW" in reason_codes,
            "low_margin_rejection": any(code.startswith("LOW_MARGIN") for code in reason_codes),
            "stale_model": any(code.startswith("MODEL_STALE") for code in reason_codes),
            "feature_drift": False,
        },
        "severity": severity,
        "recommendation": recommendation,
        "reason_codes": reason_codes,
    }


def should_emit_quality_event(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    previous = previous or {}
    if current.get("severity") not in {"warning", "critical", "healthy"}:
        return False
    return (
        previous.get("severity") != current.get("severity")
        or previous.get("recommendation") != current.get("recommendation")
        or previous.get("reason_codes") != current.get("reason_codes")
    )
