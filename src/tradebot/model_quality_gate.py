from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MODEL_QUALITY_GATE_CONTRACT_VERSION = "4B.4.3.6.6.24B"
BLOCKING_RUNTIME_SEVERITIES = {"critical", "disabled", "no_data"}
WARMUP_RUNTIME_SEVERITIES = {"warming_up"}
ACTION_CLASS_KEYS = ("1", "2")
HOLD_CLASS_KEY = "0"


@dataclass(slots=True)
class ModelQualityGateConfig:
    enabled: bool = True
    min_runtime_samples: int = 30
    block_runtime_warming_up: bool = True
    block_runtime_warning: bool = False
    min_clean_samples: int = 1_000
    min_action_coverage: float = 0.03
    max_hold_rate: float = 0.97
    max_low_margin_reject_rate: float = 0.75
    min_calibrated_accuracy: float = 0.30
    block_reload_on_insufficient_evidence: bool = True
    min_target_action_rate: float = 0.03
    max_target_hold_rate: float = 0.97
    min_present_target_classes: int = 2
    block_synthetic_class_padding: bool = True


def config_from_settings(settings: Any) -> ModelQualityGateConfig:
    return ModelQualityGateConfig(
        enabled=bool(getattr(settings, "model_quality_gate_enabled", True)),
        min_runtime_samples=int(getattr(settings, "model_quality_gate_min_runtime_samples", 30) or 30),
        block_runtime_warming_up=bool(getattr(settings, "model_quality_gate_block_runtime_warming_up", True)),
        block_runtime_warning=bool(getattr(settings, "model_quality_gate_block_runtime_warning", False)),
        min_clean_samples=int(getattr(settings, "model_quality_gate_min_clean_samples", 1_000) or 1_000),
        min_action_coverage=float(getattr(settings, "model_quality_gate_min_action_coverage", 0.03) or 0.03),
        max_hold_rate=float(getattr(settings, "model_quality_gate_max_hold_rate", 0.97) or 0.97),
        max_low_margin_reject_rate=float(getattr(settings, "model_quality_gate_max_low_margin_reject_rate", 0.75) or 0.75),
        min_calibrated_accuracy=float(getattr(settings, "model_quality_gate_min_calibrated_accuracy", 0.30) or 0.30),
        block_reload_on_insufficient_evidence=bool(getattr(settings, "model_quality_gate_block_reload_on_insufficient_evidence", True)),
        min_target_action_rate=float(getattr(settings, "model_quality_gate_min_target_action_rate", 0.03) or 0.03),
        max_target_hold_rate=float(getattr(settings, "model_quality_gate_max_target_hold_rate", 0.97) or 0.97),
        min_present_target_classes=int(getattr(settings, "model_quality_gate_min_present_target_classes", 2) or 2),
        block_synthetic_class_padding=bool(getattr(settings, "model_quality_gate_block_synthetic_class_padding", True)),
    )


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


def _rate_from_count_map(counts: Mapping[str, Any], key: str) -> float | None:
    values: dict[str, int] = {}
    for raw_key, raw_value in counts.items():
        parsed = _safe_int(raw_value)
        if parsed is None:
            continue
        values[str(raw_key)] = parsed
    total = sum(values.values())
    if total <= 0:
        return None
    return float(values.get(key, 0)) / float(total)


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _decision_from_reasons(reasons: list[str], warnings: list[str]) -> str:
    if reasons:
        return "BLOCK"
    if warnings:
        return "WARN"
    return "PASS"


def build_runtime_model_quality_gate(
    snapshot: Mapping[str, Any] | None,
    *,
    config: ModelQualityGateConfig | None = None,
    settings: Any | None = None,
) -> dict[str, Any]:
    cfg = config or (config_from_settings(settings) if settings is not None else ModelQualityGateConfig())
    snapshot = dict(snapshot or {})
    reasons: list[str] = []
    warnings: list[str] = []

    if not cfg.enabled:
        return {
            "contract_version": MODEL_QUALITY_GATE_CONTRACT_VERSION,
            "enabled": False,
            "gate_type": "runtime",
            "decision": "DISABLED",
            "ok": True,
            "reload_allowed": True,
            "live_demo_allowed": False,
            "live_real_allowed": False,
            "reason_codes": ["MODEL_QUALITY_GATE_DISABLED"],
            "warnings": [],
            "metrics": {},
        }

    severity = str(snapshot.get("severity") or "no_data").lower()
    recommendation = str(snapshot.get("recommendation") or "OK").upper()
    sample_count = _safe_int(snapshot.get("sample_count")) or 0
    distribution_pct = snapshot.get("prediction_distribution_pct") if isinstance(snapshot.get("prediction_distribution_pct"), Mapping) else {}
    confidence = snapshot.get("confidence") if isinstance(snapshot.get("confidence"), Mapping) else {}
    calibration = snapshot.get("calibration") if isinstance(snapshot.get("calibration"), Mapping) else {}

    hold_pct = _safe_float(distribution_pct.get("HOLD"))
    action_pct = None if hold_pct is None else max(0.0, 100.0 - hold_pct)
    avg_confidence = _safe_float(confidence.get("avg"))
    low_margin_pct = _safe_float(calibration.get("reject_low_margin_pct"))

    if not snapshot:
        _append_unique(reasons, "MODEL_QUALITY_SNAPSHOT_MISSING")
    if severity in BLOCKING_RUNTIME_SEVERITIES:
        _append_unique(reasons, f"MODEL_QUALITY_{severity.upper()}")
    if severity in WARMUP_RUNTIME_SEVERITIES and cfg.block_runtime_warming_up:
        _append_unique(reasons, "MODEL_QUALITY_WARMING_UP")
    if severity == "warning":
        target = reasons if cfg.block_runtime_warning else warnings
        _append_unique(target, "MODEL_QUALITY_WARNING")
    if recommendation == "RETRAIN_RECOMMENDED":
        _append_unique(reasons, "RETRAIN_RECOMMENDED")
    if sample_count < cfg.min_runtime_samples:
        _append_unique(reasons, "MODEL_QUALITY_SAMPLE_COUNT_LOW")
    if hold_pct is not None and hold_pct >= cfg.max_hold_rate * 100.0:
        _append_unique(reasons, "RUNTIME_HOLD_RATE_TOO_HIGH")
    if action_pct is not None and action_pct < cfg.min_action_coverage * 100.0:
        _append_unique(reasons, "RUNTIME_ACTION_COVERAGE_LOW")
    if low_margin_pct is not None and low_margin_pct >= cfg.max_low_margin_reject_rate * 100.0:
        _append_unique(reasons, "RUNTIME_LOW_MARGIN_REJECTION_HIGH")

    decision = _decision_from_reasons(reasons, warnings)
    return {
        "contract_version": MODEL_QUALITY_GATE_CONTRACT_VERSION,
        "enabled": True,
        "gate_type": "runtime",
        "decision": decision,
        "ok": decision != "BLOCK",
        "reload_allowed": True,
        "live_demo_allowed": decision == "PASS",
        "live_real_allowed": decision == "PASS",
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "severity": severity,
            "recommendation": recommendation,
            "sample_count": sample_count,
            "min_runtime_samples": cfg.min_runtime_samples,
            "hold_pct": hold_pct,
            "action_pct": action_pct,
            "avg_confidence": avg_confidence,
            "low_margin_rejection_pct": low_margin_pct,
        },
    }



def _normalize_distribution(raw: Mapping[str, Any] | Mapping[int, Any] | None) -> dict[str, int]:
    out = {"0": 0, "1": 0, "2": 0}
    if not isinstance(raw, Mapping):
        return out
    for key, value in raw.items():
        parsed = _safe_int(value)
        if parsed is None:
            continue
        out[str(key)] = max(0, int(parsed))
    return out


def _distribution_rate(counts: Mapping[str, int], key: str) -> float | None:
    total = int(sum(int(v) for v in counts.values()))
    if total <= 0:
        return None
    return float(int(counts.get(key, 0))) / float(total)


def _target_distribution_from_result(result: Mapping[str, Any]) -> dict[str, int] | None:
    for key in ("raw_target_distribution", "target_distribution", "training_target_distribution"):
        value = result.get(key)
        if isinstance(value, Mapping):
            return _normalize_distribution(value)
    return None


def evaluate_training_result_quality(
    result: Mapping[str, Any] | None,
    *,
    config: ModelQualityGateConfig | None = None,
    settings: Any | None = None,
) -> dict[str, Any]:
    cfg = config or (config_from_settings(settings) if settings is not None else ModelQualityGateConfig())
    result = dict(result or {})
    reasons: list[str] = []
    warnings: list[str] = []

    if not cfg.enabled:
        return {
            "contract_version": MODEL_QUALITY_GATE_CONTRACT_VERSION,
            "enabled": False,
            "gate_type": "training_result",
            "decision": "DISABLED",
            "ok": True,
            "reload_allowed": True,
            "reason_codes": ["MODEL_QUALITY_GATE_DISABLED"],
            "warnings": [],
            "metrics": {},
        }

    clean_samples = _safe_int(result.get("clean_samples"))
    calibrated_accuracy = _safe_float(result.get("calibrated_accuracy"))
    action_report = result.get("calibrated_action_report") if isinstance(result.get("calibrated_action_report"), Mapping) else {}
    action_coverage = _safe_float(action_report.get("action_coverage") or action_report.get("non_hold_rate"))
    hold_rate = _safe_float(action_report.get("hold_rate"))
    reason_counts = result.get("calibrated_reason_counts") if isinstance(result.get("calibrated_reason_counts"), Mapping) else {}
    class_distribution = result.get("calibrated_predicted_class_distribution") if isinstance(result.get("calibrated_predicted_class_distribution"), Mapping) else {}
    synthetic_class_padding_applied = bool(result.get("synthetic_class_padding_applied", False))
    target_distribution = _target_distribution_from_result(result)
    target_hold_rate = _distribution_rate(target_distribution, HOLD_CLASS_KEY) if target_distribution is not None else None
    target_action_rate = None if target_hold_rate is None else max(0.0, 1.0 - target_hold_rate)
    present_target_classes = None if target_distribution is None else int(sum(1 for value in target_distribution.values() if int(value) > 0))

    if hold_rate is None and class_distribution:
        hold_rate = _rate_from_count_map(class_distribution, HOLD_CLASS_KEY)
    if action_coverage is None and hold_rate is not None:
        action_coverage = max(0.0, 1.0 - hold_rate)

    low_margin_reject_count = sum(
        int(_safe_int(value) or 0)
        for key, value in reason_counts.items()
        if "LOW_MARGIN" in str(key).upper() or "INDECISION" in str(key).upper()
    )
    total_reason_count = sum(int(_safe_int(value) or 0) for value in reason_counts.values())
    low_margin_reject_rate = None if total_reason_count <= 0 else float(low_margin_reject_count) / float(total_reason_count)

    missing_metrics: list[str] = []
    if clean_samples is None:
        missing_metrics.append("clean_samples")
    if action_coverage is None:
        missing_metrics.append("action_coverage")
    if hold_rate is None:
        missing_metrics.append("hold_rate")
    if calibrated_accuracy is None:
        missing_metrics.append("calibrated_accuracy")

    if missing_metrics:
        target = reasons if cfg.block_reload_on_insufficient_evidence else warnings
        _append_unique(target, "TRAINING_QUALITY_EVIDENCE_INSUFFICIENT")
    if clean_samples is not None and clean_samples < cfg.min_clean_samples:
        _append_unique(reasons, "TRAINING_CLEAN_SAMPLE_COUNT_LOW")
    if action_coverage is not None and action_coverage < cfg.min_action_coverage:
        _append_unique(reasons, "TRAINING_ACTION_COVERAGE_LOW")
    if hold_rate is not None and hold_rate > cfg.max_hold_rate:
        _append_unique(reasons, "TRAINING_HOLD_RATE_TOO_HIGH")
    if calibrated_accuracy is not None and calibrated_accuracy < cfg.min_calibrated_accuracy:
        _append_unique(reasons, "TRAINING_CALIBRATED_ACCURACY_LOW")
    if low_margin_reject_rate is not None and low_margin_reject_rate > cfg.max_low_margin_reject_rate:
        _append_unique(reasons, "TRAINING_LOW_MARGIN_REJECTION_HIGH")
    if synthetic_class_padding_applied and cfg.block_synthetic_class_padding:
        _append_unique(reasons, "TRAINING_SYNTHETIC_CLASS_PADDING_USED")
    if target_action_rate is not None and target_action_rate < cfg.min_target_action_rate:
        _append_unique(reasons, "TRAINING_TARGET_ACTION_RATE_LOW")
    if target_hold_rate is not None and target_hold_rate > cfg.max_target_hold_rate:
        _append_unique(reasons, "TRAINING_TARGET_HOLD_RATE_TOO_HIGH")
    if present_target_classes is not None and present_target_classes < cfg.min_present_target_classes:
        _append_unique(reasons, "TRAINING_TARGET_CLASS_COVERAGE_LOW")

    decision = _decision_from_reasons(reasons, warnings)
    return {
        "contract_version": MODEL_QUALITY_GATE_CONTRACT_VERSION,
        "enabled": True,
        "gate_type": "training_result",
        "decision": decision,
        "ok": decision != "BLOCK",
        "reload_allowed": decision != "BLOCK",
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "clean_samples": clean_samples,
            "min_clean_samples": cfg.min_clean_samples,
            "calibrated_accuracy": calibrated_accuracy,
            "min_calibrated_accuracy": cfg.min_calibrated_accuracy,
            "action_coverage": action_coverage,
            "min_action_coverage": cfg.min_action_coverage,
            "hold_rate": hold_rate,
            "max_hold_rate": cfg.max_hold_rate,
            "low_margin_reject_rate": low_margin_reject_rate,
            "max_low_margin_reject_rate": cfg.max_low_margin_reject_rate,
            "target_distribution": target_distribution,
            "target_hold_rate": target_hold_rate,
            "max_target_hold_rate": cfg.max_target_hold_rate,
            "target_action_rate": target_action_rate,
            "min_target_action_rate": cfg.min_target_action_rate,
            "present_target_classes": present_target_classes,
            "min_present_target_classes": cfg.min_present_target_classes,
            "synthetic_class_padding_applied": synthetic_class_padding_applied,
            "missing_metrics": missing_metrics,
        },
    }
