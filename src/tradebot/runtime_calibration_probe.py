from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION = "4B.4.3.6.6.24E"
CLASS_TO_SIGNAL = {0: "HOLD", 1: "BUY", 2: "SELL"}
SIGNAL_TO_CLASS = {value: key for key, value in CLASS_TO_SIGNAL.items()}
ACTION_SIGNALS = {"BUY", "SELL"}


@dataclass(frozen=True, slots=True)
class ThresholdProfile:
    name: str
    buy_threshold: float = 0.64
    sell_threshold: float = 0.57
    hold_band_low: float = 0.45
    hold_band_high: float = 0.55
    indecision_margin: float = 0.08

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_THRESHOLD_PROFILE = ThresholdProfile(name="runtime_default")
DIAGNOSTIC_THRESHOLD_PROFILES: tuple[ThresholdProfile, ...] = (
    ThresholdProfile(name="runtime_default", buy_threshold=0.64, sell_threshold=0.57, hold_band_low=0.45, hold_band_high=0.55, indecision_margin=0.08),
    ThresholdProfile(name="action_seek_light", buy_threshold=0.55, sell_threshold=0.52, hold_band_low=0.42, hold_band_high=0.58, indecision_margin=0.04),
    ThresholdProfile(name="action_seek_medium", buy_threshold=0.50, sell_threshold=0.50, hold_band_low=0.40, hold_band_high=0.60, indecision_margin=0.02),
    ThresholdProfile(name="no_margin_probe", buy_threshold=0.45, sell_threshold=0.45, hold_band_low=0.35, hold_band_high=0.65, indecision_margin=0.00),
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


def get_path(data: Any, path: str, default: Any = None) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, Mapping):
            cur = cur.get(part, default)
        else:
            return default
    return cur


def signal_from_class(value: Any) -> str:
    parsed = _safe_int(value)
    return CLASS_TO_SIGNAL.get(parsed if parsed is not None else -1, "HOLD")


def class_from_signal(value: Any) -> int:
    return SIGNAL_TO_CLASS.get(str(value or "HOLD").upper(), 0)


def _probability_triplet_from_mapping(metrics: Mapping[str, Any]) -> tuple[float, float, float] | None:
    hold = _safe_float(metrics.get("holdProbability") or metrics.get("hold_probability") or metrics.get("hold_p"))
    buy = _safe_float(metrics.get("buyProbability") or metrics.get("buy_probability") or metrics.get("buy_p"))
    sell = _safe_float(metrics.get("sellProbability") or metrics.get("sell_probability") or metrics.get("sell_p"))
    if hold is None or buy is None or sell is None:
        return None
    return float(hold), float(buy), float(sell)


def _first_mapping(*values: Any) -> Mapping[str, Any]:
    for value in values:
        if isinstance(value, Mapping):
            return value
    return {}


def extract_runtime_probability_sample(status: Mapping[str, Any], *, sample_index: int = 0) -> dict[str, Any] | None:
    """Extract one probability/calibration observation from a /status payload.

    The function is intentionally tolerant because status payloads evolved across
    4B.4.3.6.6.x. It checks the modern AI metrics first, then decision-audit
    fallbacks. It returns None if the payload contains no model probabilities.
    """
    ai_snapshot = _first_mapping(status.get("ai_snapshot"))
    ai_metrics = _first_mapping(ai_snapshot.get("metrics"), status.get("last_signal_metrics"), get_path(status, "decision_audit_snapshot.ai"))
    probabilities = _probability_triplet_from_mapping(ai_metrics)
    if probabilities is None:
        return None

    hold_p, buy_p, sell_p = probabilities
    probs = [hold_p, buy_p, sell_p]
    raw_class = _safe_int(ai_metrics.get("rawPredictedClass") or ai_metrics.get("raw_predicted_class"))
    if raw_class is None:
        raw_class = max(range(3), key=lambda idx: probs[idx])
    raw_signal = signal_from_class(raw_class)
    confidence = _safe_float(ai_metrics.get("rawTopProbability") or ai_metrics.get("raw_top_probability") or ai_metrics.get("confidence"))
    if confidence is None:
        confidence = float(probs[int(raw_class)])
    margin = _safe_float(ai_metrics.get("rawMargin") or ai_metrics.get("raw_margin"))
    if margin is None:
        margin = abs(buy_p - sell_p)

    current_signal = str(status.get("last_signal") or get_path(status, "decision_audit_snapshot.effective_decision.signal") or get_path(status, "ai_snapshot.signal") or "HOLD").upper()
    calibrated_class = _safe_int(ai_metrics.get("calibratedClass") or ai_metrics.get("calibrated_class"))
    calibrated_signal = signal_from_class(calibrated_class) if calibrated_class is not None else current_signal
    calibration_reason = str(ai_metrics.get("calibrationReason") or ai_metrics.get("calibration_reason") or get_path(status, "decision_audit_snapshot.threshold_trace.calibration_reason") or "UNKNOWN")
    threshold_trace = _first_mapping(status.get("threshold_trace"), get_path(status, "decision_audit_snapshot.threshold_trace"), get_path(status, "ai_snapshot.threshold_config"), get_path(status, "config_safety_snapshot.ai"))

    return {
        "contract_version": RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION,
        "sample_index": int(sample_index),
        "symbol": status.get("symbol"),
        "model_path": get_path(status, "ai_snapshot.model_path"),
        "close_time": status.get("last_evaluated_close_time") or get_path(status, "decision_audit_snapshot.close_time") or get_path(status, "ai_snapshot.last_evaluated_close_time"),
        "raw_predicted_class": int(raw_class),
        "raw_signal": raw_signal,
        "current_signal": current_signal,
        "calibrated_signal": calibrated_signal,
        "calibrated_class": class_from_signal(calibrated_signal),
        "calibration_reason": calibration_reason,
        "hold_probability": hold_p,
        "buy_probability": buy_p,
        "sell_probability": sell_p,
        "raw_top_probability": float(confidence),
        "raw_margin": float(margin),
        "threshold_trace": dict(threshold_trace),
    }


def threshold_profile_from_mapping(raw: Mapping[str, Any] | None, *, name: str = "current_runtime") -> ThresholdProfile:
    raw = raw or {}
    return ThresholdProfile(
        name=name,
        buy_threshold=float(_safe_float(raw.get("buy_threshold")) if _safe_float(raw.get("buy_threshold")) is not None else DEFAULT_THRESHOLD_PROFILE.buy_threshold),
        sell_threshold=float(_safe_float(raw.get("sell_threshold")) if _safe_float(raw.get("sell_threshold")) is not None else DEFAULT_THRESHOLD_PROFILE.sell_threshold),
        hold_band_low=float(_safe_float(raw.get("hold_band_low")) if _safe_float(raw.get("hold_band_low")) is not None else DEFAULT_THRESHOLD_PROFILE.hold_band_low),
        hold_band_high=float(_safe_float(raw.get("hold_band_high")) if _safe_float(raw.get("hold_band_high")) is not None else DEFAULT_THRESHOLD_PROFILE.hold_band_high),
        indecision_margin=float(_safe_float(raw.get("indecision_margin")) if _safe_float(raw.get("indecision_margin")) is not None else DEFAULT_THRESHOLD_PROFILE.indecision_margin),
    )


def calibrate_probabilities(hold_p: float, buy_p: float, sell_p: float, profile: ThresholdProfile) -> dict[str, Any]:
    probs = [float(hold_p), float(buy_p), float(sell_p)]
    predicted_class = max(range(3), key=lambda idx: probs[idx])
    raw_signal = signal_from_class(predicted_class)
    confidence = float(probs[predicted_class])
    margin = abs(float(buy_p) - float(sell_p))

    signal = "HOLD"
    reason = "RAW_TOP_HOLD"
    raw_buy_accept = raw_signal == "BUY" and buy_p >= profile.hold_band_low and buy_p > hold_p and margin >= profile.indecision_margin
    raw_sell_accept = raw_signal == "SELL" and sell_p >= profile.hold_band_low and sell_p > hold_p and margin >= profile.indecision_margin

    if raw_buy_accept:
        signal = "BUY"
        reason = "RAW_ACTION_FIRST_ACCEPT"
    elif raw_sell_accept:
        signal = "SELL"
        reason = "RAW_ACTION_FIRST_ACCEPT"
    elif raw_signal == "BUY" and buy_p >= profile.buy_threshold:
        signal = "BUY"
        reason = "RAW_ACTION_HIGH_BAND_ACCEPT"
    elif raw_signal == "SELL" and sell_p >= profile.sell_threshold:
        signal = "SELL"
        reason = "RAW_ACTION_HIGH_BAND_ACCEPT"
    else:
        signal = "HOLD"
        if raw_signal != "HOLD" and hold_p >= profile.hold_band_high:
            reason = "REJECT_HOLD_DOMINANCE"
        elif margin < profile.indecision_margin:
            reason = "REJECT_LOW_MARGIN"
        elif raw_signal != "HOLD":
            reason = "REJECT_LOW_ACTION_PROB"

    return {
        "profile": profile.name,
        "raw_predicted_class": predicted_class,
        "raw_signal": raw_signal,
        "calibrated_signal": signal,
        "calibrated_class": class_from_signal(signal),
        "calibration_reason": reason,
        "confidence": confidence,
        "raw_margin": margin,
    }


def build_threshold_profiles(samples: Sequence[Mapping[str, Any]], *, include_current: bool = True) -> list[ThresholdProfile]:
    profiles: list[ThresholdProfile] = []
    if include_current:
        first_trace = None
        for sample in samples:
            trace = sample.get("threshold_trace")
            if isinstance(trace, Mapping) and trace:
                first_trace = trace
                break
        profiles.append(threshold_profile_from_mapping(first_trace, name="current_runtime"))
    seen = {profile.name for profile in profiles}
    for profile in DIAGNOSTIC_THRESHOLD_PROFILES:
        if profile.name not in seen:
            profiles.append(profile)
            seen.add(profile.name)
    return profiles


def _distribution(values: Iterable[str]) -> dict[str, int]:
    counter = Counter(str(value).upper() for value in values)
    return {key: int(counter.get(key, 0)) for key in ("HOLD", "BUY", "SELL")}


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((float(part) / float(total)) * 100.0, 6)


def _action_pct(distribution: Mapping[str, Any]) -> float:
    total = sum(int(distribution.get(key, 0) or 0) for key in ("HOLD", "BUY", "SELL"))
    action = int(distribution.get("BUY", 0) or 0) + int(distribution.get("SELL", 0) or 0)
    return _pct(action, total)


def build_threshold_sweep(samples: Sequence[Mapping[str, Any]], profiles: Sequence[ThresholdProfile] | None = None) -> dict[str, Any]:
    sample_list = [dict(sample) for sample in samples]
    profiles = list(profiles or build_threshold_profiles(sample_list))
    per_profile: list[dict[str, Any]] = []
    for profile in profiles:
        calibrated_signals: list[str] = []
        raw_signals: list[str] = []
        reason_counts: Counter[str] = Counter()
        for sample in sample_list:
            result = calibrate_probabilities(
                float(sample["hold_probability"]),
                float(sample["buy_probability"]),
                float(sample["sell_probability"]),
                profile,
            )
            calibrated_signals.append(str(result["calibrated_signal"]))
            raw_signals.append(str(result["raw_signal"]))
            reason_counts[str(result["calibration_reason"])] += 1
        calibrated_distribution = _distribution(calibrated_signals)
        raw_distribution = _distribution(raw_signals)
        per_profile.append({
            "profile": profile.to_dict(),
            "raw_distribution": raw_distribution,
            "calibrated_distribution": calibrated_distribution,
            "action_pct": _action_pct(calibrated_distribution),
            "hold_pct": _pct(int(calibrated_distribution.get("HOLD", 0) or 0), len(sample_list)),
            "reason_counts": dict(sorted(reason_counts.items())),
        })
    return {
        "contract_version": RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION,
        "report_type": "threshold_sweep",
        "sample_count": len(sample_list),
        "profiles": per_profile,
    }


def build_runtime_calibration_probe(samples: Sequence[Mapping[str, Any]], *, min_samples: int = 30) -> dict[str, Any]:
    sample_list = [dict(sample) for sample in samples]
    sample_count = len(sample_list)
    raw_distribution = _distribution(sample.get("raw_signal", "HOLD") for sample in sample_list)
    current_distribution = _distribution(sample.get("calibrated_signal") or sample.get("current_signal") or "HOLD" for sample in sample_list)
    actual_reason_counts = Counter(str(sample.get("calibration_reason") or "UNKNOWN") for sample in sample_list)
    low_margin_count = int(actual_reason_counts.get("REJECT_LOW_MARGIN", 0))
    threshold_sweep = build_threshold_sweep(sample_list) if sample_list else build_threshold_sweep([])
    raw_action_pct = _action_pct(raw_distribution)
    current_action_pct = _action_pct(current_distribution)
    low_margin_pct = _pct(low_margin_count, sample_count)
    relaxed_action_pct = 0.0
    best_relaxed_profile = None
    for profile in threshold_sweep.get("profiles", []):
        if profile.get("profile", {}).get("name") == "current_runtime":
            continue
        action_pct = float(profile.get("action_pct") or 0.0)
        if action_pct > relaxed_action_pct:
            relaxed_action_pct = action_pct
            best_relaxed_profile = profile.get("profile", {}).get("name")

    blockers: list[str] = []
    warnings: list[str] = []
    if sample_count < min_samples:
        blockers.append("PROBE_SAMPLE_COUNT_LOW")
    if raw_action_pct <= 0.0:
        blockers.append("RAW_ACTION_COVERAGE_ZERO")
    if current_action_pct <= 0.0:
        blockers.append("CURRENT_ACTION_COVERAGE_ZERO")
    if low_margin_pct >= 75.0:
        blockers.append("LOW_MARGIN_REJECTION_HIGH")
    if relaxed_action_pct > current_action_pct:
        warnings.append("RELAXED_THRESHOLDS_INCREASE_ACTION_COVERAGE")

    if sample_count < min_samples:
        conclusion = "PENDING_INSUFFICIENT_SAMPLES"
    elif raw_action_pct <= 0.0:
        conclusion = "RAW_MODEL_COLLAPSE"
    elif current_action_pct <= 0.0 and relaxed_action_pct > 0.0:
        conclusion = "CALIBRATION_SUPPRESSION"
    elif current_action_pct <= 0.0:
        conclusion = "MODEL_ACTION_PROBABILITY_TOO_LOW"
    else:
        conclusion = "ACTIONABLE_UNDER_CURRENT_CALIBRATION"

    decision = "BLOCK" if blockers else ("WARN" if warnings else "PASS")
    recommendation = {
        "PENDING_INSUFFICIENT_SAMPLES": "Accumulate more runtime samples before changing thresholds.",
        "RAW_MODEL_COLLAPSE": "Do not relax thresholds; investigate labeling, features, class mapping, and model objective because raw top class is not actionable.",
        "CALIBRATION_SUPPRESSION": "Threshold/calibration tuning may be investigated with paper-only validation; do not bypass the model gate.",
        "MODEL_ACTION_PROBABILITY_TOO_LOW": "Retrain or adjust objective/features; raw action exists but probabilities are too weak for even diagnostic profiles.",
        "ACTIONABLE_UNDER_CURRENT_CALIBRATION": "Current calibration emits actionable signals; continue controlled demo/paper validation.",
    }.get(conclusion, "Review probe report.")

    return {
        "contract_version": RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION,
        "report_type": "runtime_calibration_probe",
        "decision": decision,
        "ok": decision != "BLOCK",
        "observation_only": True,
        "no_post_actions": True,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "sample_count": sample_count,
        "min_samples": int(min_samples),
        "conclusion": conclusion,
        "recommendation": recommendation,
        "reason_codes": blockers,
        "warnings": warnings,
        "metrics": {
            "raw_distribution": raw_distribution,
            "raw_action_pct": raw_action_pct,
            "current_distribution": current_distribution,
            "current_action_pct": current_action_pct,
            "actual_calibration_reason_counts": dict(sorted(actual_reason_counts.items())),
            "low_margin_rejection_pct": low_margin_pct,
            "relaxed_best_action_pct": relaxed_action_pct,
            "relaxed_best_profile": best_relaxed_profile,
        },
        "threshold_sweep": threshold_sweep,
        "samples": sample_list,
    }
