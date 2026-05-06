from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

from ..model_quality_gate import ModelQualityGateConfig, evaluate_training_result_quality

RETRAIN_RECOVERY_CONTRACT_VERSION = "4B.4.3.6.6.24D"
HOLD_CLASS_KEY = "0"
ACTION_CLASS_KEYS = ("1", "2")


@dataclass(frozen=True, slots=True)
class DatasetQualityConfig:
    min_clean_samples: int = 1_000
    min_target_action_rate: float = 0.03
    max_target_hold_rate: float = 0.97
    min_present_target_classes: int = 2
    block_synthetic_class_padding: bool = True


@dataclass(frozen=True, slots=True)
class RetrainCandidateSpec:
    days: int
    class_weight_profile: str
    threshold_profile: str
    feature_lag: int | None = None

    def slug(self) -> str:
        lag = "auto" if self.feature_lag is None else str(int(self.feature_lag))
        return f"{int(self.days)}d_{self.class_weight_profile}_{self.threshold_profile}_lag{lag}".replace(" ", "_")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def normalize_class_distribution(raw: Mapping[str, Any] | Mapping[int, Any] | None) -> dict[str, int]:
    out: dict[str, int] = {"0": 0, "1": 0, "2": 0}
    if not isinstance(raw, Mapping):
        return out
    for key, value in raw.items():
        parsed = _safe_int(value)
        if parsed is None:
            continue
        out[str(key)] = max(0, int(parsed))
    for key in ("0", "1", "2"):
        out.setdefault(key, 0)
    return out


def class_distribution_rates(counts: Mapping[str, Any] | None) -> dict[str, float]:
    normalized = normalize_class_distribution(counts)
    total = int(sum(normalized.values()))
    if total <= 0:
        return {key: 0.0 for key in sorted(normalized)}
    return {key: float(value) / float(total) for key, value in sorted(normalized.items())}


def _extract_target_distribution(result: Mapping[str, Any]) -> dict[str, int]:
    for key in (
        "raw_target_distribution",
        "target_distribution",
        "training_target_distribution",
    ):
        value = result.get(key)
        if isinstance(value, Mapping):
            return normalize_class_distribution(value)
    manifest = result.get("dataset_manifest")
    if isinstance(manifest, Mapping) and isinstance(manifest.get("target_distribution"), Mapping):
        return normalize_class_distribution(manifest.get("target_distribution"))
    prediction_distribution = result.get("prediction_distribution")
    if isinstance(prediction_distribution, Mapping) and isinstance(prediction_distribution.get("actual_class_distribution"), Mapping):
        return normalize_class_distribution(prediction_distribution.get("actual_class_distribution"))
    return normalize_class_distribution(None)


def build_dataset_quality_report(
    result: Mapping[str, Any] | None,
    *,
    config: DatasetQualityConfig | None = None,
) -> dict[str, Any]:
    cfg = config or DatasetQualityConfig()
    result = dict(result or {})
    reasons: list[str] = []
    warnings: list[str] = []

    clean_samples = _safe_int(result.get("clean_samples"))
    synthetic_padding = bool(result.get("synthetic_class_padding_applied", False))
    target_counts = _extract_target_distribution(result)
    total_targets = int(sum(target_counts.values()))
    target_rates = class_distribution_rates(target_counts)
    hold_rate = float(target_rates.get(HOLD_CLASS_KEY, 0.0))
    action_rate = max(0.0, 1.0 - hold_rate)
    present_classes = int(sum(1 for count in target_counts.values() if int(count) > 0))
    present_action_classes = int(sum(1 for key in ACTION_CLASS_KEYS if int(target_counts.get(key, 0)) > 0))

    if clean_samples is None:
        _append_unique(warnings, "TRAINING_CLEAN_SAMPLE_COUNT_MISSING")
    elif clean_samples < cfg.min_clean_samples:
        _append_unique(reasons, "DATASET_CLEAN_SAMPLE_COUNT_LOW")

    if total_targets <= 0:
        _append_unique(reasons, "TARGET_DISTRIBUTION_MISSING")
    else:
        if action_rate < cfg.min_target_action_rate:
            _append_unique(reasons, "TARGET_ACTION_RATE_LOW")
        if hold_rate > cfg.max_target_hold_rate:
            _append_unique(reasons, "TARGET_HOLD_RATE_TOO_HIGH")
        if present_classes < cfg.min_present_target_classes:
            _append_unique(reasons, "TARGET_CLASS_COVERAGE_LOW")
        if present_action_classes <= 0:
            _append_unique(reasons, "TARGET_ACTION_CLASS_MISSING")

    if synthetic_padding and cfg.block_synthetic_class_padding:
        _append_unique(reasons, "SYNTHETIC_CLASS_PADDING_USED")

    decision = "BLOCK" if reasons else ("WARN" if warnings else "PASS")
    return {
        "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
        "report_type": "dataset_quality",
        "decision": decision,
        "ok": decision != "BLOCK",
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "clean_samples": clean_samples,
            "min_clean_samples": cfg.min_clean_samples,
            "target_distribution": target_counts,
            "target_distribution_rate": target_rates,
            "target_total": total_targets,
            "target_hold_rate": hold_rate,
            "max_target_hold_rate": cfg.max_target_hold_rate,
            "target_action_rate": action_rate,
            "min_target_action_rate": cfg.min_target_action_rate,
            "present_target_classes": present_classes,
            "min_present_target_classes": cfg.min_present_target_classes,
            "present_action_classes": present_action_classes,
            "synthetic_class_padding_applied": synthetic_padding,
        },
    }


def evaluate_retrain_candidate(
    result: Mapping[str, Any] | None,
    *,
    gate_config: ModelQualityGateConfig | None = None,
    dataset_config: DatasetQualityConfig | None = None,
    candidate_spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(result or {})
    gate = evaluate_training_result_quality(result, config=gate_config)
    dataset_quality = build_dataset_quality_report(result, config=dataset_config)

    reasons: list[str] = []
    warnings: list[str] = []
    if gate.get("decision") == "BLOCK":
        _append_unique(reasons, "TRAINING_GATE_BLOCK")
    if dataset_quality.get("decision") == "BLOCK":
        _append_unique(reasons, "DATASET_QUALITY_BLOCK")
    for code in gate.get("reason_codes") or []:
        _append_unique(reasons, str(code))
    for code in dataset_quality.get("reason_codes") or []:
        _append_unique(reasons, str(code))
    for code in gate.get("warnings") or []:
        _append_unique(warnings, str(code))
    for code in dataset_quality.get("warnings") or []:
        _append_unique(warnings, str(code))

    decision = "BLOCK" if reasons else ("WARN" if warnings or gate.get("decision") == "WARN" or dataset_quality.get("decision") == "WARN" else "PASS")
    return {
        "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
        "report_type": "retrain_candidate_quality",
        "decision": decision,
        "ok": decision != "BLOCK",
        "reload_allowed": decision == "PASS" and bool(gate.get("reload_allowed", False)),
        "candidate_spec": dict(candidate_spec or {}),
        "model_path": result.get("model_path") or result.get("output"),
        "reason_codes": reasons,
        "warnings": warnings,
        "quality_gate": gate,
        "dataset_quality": dataset_quality,
        "score": rank_retrain_candidate(result, gate=gate, dataset_quality=dataset_quality),
    }


def rank_retrain_candidate(
    result: Mapping[str, Any] | None,
    *,
    gate: Mapping[str, Any] | None = None,
    dataset_quality: Mapping[str, Any] | None = None,
) -> float:
    result = dict(result or {})
    gate = dict(gate or {})
    dataset_quality = dict(dataset_quality or {})

    calibrated_accuracy = _safe_float(result.get("calibrated_accuracy")) or 0.0
    action_report = result.get("calibrated_action_report") if isinstance(result.get("calibrated_action_report"), Mapping) else {}
    action_coverage = _safe_float(action_report.get("action_coverage") or action_report.get("non_hold_rate")) or 0.0
    hold_rate = _safe_float(action_report.get("hold_rate"))
    if hold_rate is None:
        hold_rate = max(0.0, 1.0 - action_coverage)
    dataset_metrics = dataset_quality.get("metrics") if isinstance(dataset_quality.get("metrics"), Mapping) else {}
    target_action_rate = _safe_float(dataset_metrics.get("target_action_rate")) or 0.0
    low_margin_rate = _safe_float((gate.get("metrics") or {}).get("low_margin_reject_rate") if isinstance(gate.get("metrics"), Mapping) else None) or 0.0

    penalty = 0.0
    if gate.get("decision") == "BLOCK" or dataset_quality.get("decision") == "BLOCK":
        penalty += 10.0
    elif gate.get("decision") == "WARN" or dataset_quality.get("decision") == "WARN":
        penalty += 1.0

    return float((calibrated_accuracy * 2.0) + action_coverage + (target_action_rate * 0.5) - (hold_rate * 0.25) - (low_margin_rate * 0.5) - penalty)


def select_best_retrain_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    evaluated = [dict(item) for item in candidates]
    if not evaluated:
        return {
            "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
            "decision": "BLOCK",
            "approved": False,
            "reason_codes": ["NO_CANDIDATES"],
            "best_candidate": None,
        }
    sorted_candidates = sorted(evaluated, key=lambda item: float(item.get("score") or -999.0), reverse=True)
    passing = [item for item in sorted_candidates if item.get("decision") == "PASS" and bool(item.get("reload_allowed"))]
    if passing:
        return {
            "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
            "decision": "PASS",
            "approved": True,
            "reason_codes": [],
            "best_candidate": passing[0],
            "candidate_count": len(evaluated),
            "pass_count": len(passing),
        }
    return {
        "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
        "decision": "BLOCK",
        "approved": False,
        "reason_codes": ["NO_PASSING_CANDIDATE"],
        "best_candidate": sorted_candidates[0],
        "candidate_count": len(evaluated),
        "pass_count": 0,
    }


def build_candidate_matrix(
    *,
    days: Iterable[int],
    class_weight_profiles: Iterable[str],
    threshold_profiles: Iterable[str],
    feature_lag: int | None = None,
    max_candidates: int | None = None,
) -> list[RetrainCandidateSpec]:
    matrix: list[RetrainCandidateSpec] = []
    for day in days:
        for class_weight_profile in class_weight_profiles:
            for threshold_profile in threshold_profiles:
                matrix.append(
                    RetrainCandidateSpec(
                        days=int(day),
                        class_weight_profile=str(class_weight_profile),
                        threshold_profile=str(threshold_profile),
                        feature_lag=feature_lag,
                    )
                )
                if max_candidates is not None and len(matrix) >= int(max_candidates):
                    return matrix
    return matrix


__all__ = [
    "RETRAIN_RECOVERY_CONTRACT_VERSION",
    "DatasetQualityConfig",
    "RetrainCandidateSpec",
    "build_candidate_matrix",
    "build_dataset_quality_report",
    "class_distribution_rates",
    "evaluate_retrain_candidate",
    "normalize_class_distribution",
    "select_best_retrain_candidate",
]
