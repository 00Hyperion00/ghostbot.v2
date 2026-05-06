from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from statistics import mean, median
from typing import Any, Mapping, Sequence

from tradebot.runtime_calibration_probe import ThresholdProfile, build_threshold_profiles, calibrate_probabilities

CALIBRATION_POLICY_GATE_CONTRACT_VERSION = "4B.4.3.6.6.24F"
DIAGNOSTIC_ONLY_PROFILE_NAMES = {"current_runtime", "runtime_default", "no_margin_probe"}
ZERO_MARGIN_BLOCKLIST = {"no_margin_probe"}


@dataclass(frozen=True, slots=True)
class CalibrationPolicyGateLimits:
    min_samples: int = 30
    min_action_pct: float = 2.0
    max_action_pct: float = 45.0
    max_action_side_pct: float = 85.0
    max_low_margin_reject_pct: float = 75.0
    min_indecision_margin: float = 0.002
    target_action_pct: float = 18.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CALIBRATION_CANDIDATE_PROFILES: tuple[ThresholdProfile, ...] = (
    ThresholdProfile("margin_relaxed_light", buy_threshold=0.58, sell_threshold=0.55, hold_band_low=0.43, hold_band_high=0.58, indecision_margin=0.02),
    ThresholdProfile("margin_relaxed_medium", buy_threshold=0.52, sell_threshold=0.50, hold_band_low=0.42, hold_band_high=0.58, indecision_margin=0.01),
    ThresholdProfile("margin_relaxed_micro_guarded", buy_threshold=0.48, sell_threshold=0.47, hold_band_low=0.42, hold_band_high=0.60, indecision_margin=0.004),
    ThresholdProfile("action_seek_guarded", buy_threshold=0.46, sell_threshold=0.46, hold_band_low=0.40, hold_band_high=0.62, indecision_margin=0.003),
    ThresholdProfile("asymmetric_buy_sell_guarded", buy_threshold=0.47, sell_threshold=0.45, hold_band_low=0.40, hold_band_high=0.62, indecision_margin=0.004),
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(part: int | float, total: int | float) -> float:
    if float(total) <= 0:
        return 0.0
    return round((float(part) / float(total)) * 100.0, 6)


def _distribution(values: Sequence[str]) -> dict[str, int]:
    counter = Counter(str(value or "HOLD").upper() for value in values)
    return {key: int(counter.get(key, 0)) for key in ("HOLD", "BUY", "SELL")}


def _action_pct(distribution: Mapping[str, Any]) -> float:
    total = sum(int(distribution.get(signal, 0) or 0) for signal in ("HOLD", "BUY", "SELL"))
    action = int(distribution.get("BUY", 0) or 0) + int(distribution.get("SELL", 0) or 0)
    return _pct(action, total)


def _dominant_action_pct(distribution: Mapping[str, Any]) -> float:
    buy = int(distribution.get("BUY", 0) or 0)
    sell = int(distribution.get("SELL", 0) or 0)
    action = buy + sell
    if action <= 0:
        return 0.0
    return _pct(max(buy, sell), action)


def _margin_summary(samples: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    margins = sorted(_safe_float(sample.get("raw_margin"), 0.0) for sample in samples)
    if not margins:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    return {"min": round(margins[0], 8), "median": round(float(median(margins)), 8), "mean": round(float(mean(margins)), 8), "max": round(margins[-1], 8)}


def _profile_score(action_pct: float, dominant_action_pct: float, low_margin_reject_pct: float, profile: ThresholdProfile, limits: CalibrationPolicyGateLimits) -> float:
    target_distance = abs(action_pct - limits.target_action_pct)
    side_penalty = max(0.0, dominant_action_pct - 50.0) / 10.0
    low_margin_penalty = low_margin_reject_pct / 25.0
    margin_penalty = max(0.0, limits.min_indecision_margin - profile.indecision_margin) * 100.0
    return round(100.0 - target_distance - side_penalty - low_margin_penalty - margin_penalty, 6)


def evaluate_calibration_profile(samples: Sequence[Mapping[str, Any]], profile: ThresholdProfile, *, limits: CalibrationPolicyGateLimits | None = None, approvable: bool = True) -> dict[str, Any]:
    limits = limits or CalibrationPolicyGateLimits()
    sample_list = [dict(sample) for sample in samples]
    calibrated_signals: list[str] = []
    raw_signals: list[str] = []
    reason_counts: Counter[str] = Counter()
    for sample in sample_list:
        result = calibrate_probabilities(_safe_float(sample.get("hold_probability")), _safe_float(sample.get("buy_probability")), _safe_float(sample.get("sell_probability")), profile)
        calibrated_signals.append(str(result.get("calibrated_signal") or "HOLD").upper())
        raw_signals.append(str(result.get("raw_signal") or sample.get("raw_signal") or "HOLD").upper())
        reason_counts[str(result.get("calibration_reason") or "UNKNOWN")] += 1
    sample_count = len(sample_list)
    calibrated_distribution = _distribution(calibrated_signals)
    raw_distribution = _distribution(raw_signals)
    action_pct = _action_pct(calibrated_distribution)
    raw_action_pct = _action_pct(raw_distribution)
    dominant_action_pct = _dominant_action_pct(calibrated_distribution)
    low_margin_reject_pct = _pct(int(reason_counts.get("REJECT_LOW_MARGIN", 0)), sample_count)
    blockers: list[str] = []
    warnings: list[str] = []
    if sample_count < limits.min_samples:
        blockers.append("CALIBRATION_GATE_SAMPLE_COUNT_LOW")
    if profile.name in DIAGNOSTIC_ONLY_PROFILE_NAMES or not approvable:
        blockers.append("DIAGNOSTIC_PROFILE_NOT_APPROVABLE")
    if profile.name in ZERO_MARGIN_BLOCKLIST or profile.indecision_margin <= 0.0:
        blockers.append("ZERO_MARGIN_PROFILE_NOT_APPROVABLE")
    if profile.indecision_margin < limits.min_indecision_margin:
        blockers.append("INDECISION_MARGIN_BELOW_FLOOR")
    if raw_action_pct <= 0.0:
        blockers.append("RAW_ACTION_COVERAGE_ZERO")
    if action_pct <= 0.0 or action_pct < limits.min_action_pct:
        blockers.append("CALIBRATED_ACTION_COVERAGE_LOW")
    if action_pct > limits.max_action_pct:
        blockers.append("CALIBRATED_ACTION_COVERAGE_TOO_HIGH")
    if dominant_action_pct > limits.max_action_side_pct:
        blockers.append("ACTION_SIDE_IMBALANCE_HIGH")
    if low_margin_reject_pct > limits.max_low_margin_reject_pct:
        blockers.append("LOW_MARGIN_REJECTION_REMAINS_HIGH")
    if action_pct > 0.0 and action_pct < limits.min_action_pct * 2.0:
        warnings.append("ACTION_COVERAGE_BARELY_ABOVE_FLOOR")
    if dominant_action_pct > 70.0 and dominant_action_pct <= limits.max_action_side_pct:
        warnings.append("ACTION_SIDE_IMBALANCE_ELEVATED")
    if profile.name in {"action_seek_guarded", "asymmetric_buy_sell_guarded"}:
        warnings.append("PAPER_ONLY_CANDIDATE_PROFILE")
    decision = "BLOCK" if blockers else ("WARN" if warnings else "PASS")
    score = _profile_score(action_pct, dominant_action_pct, low_margin_reject_pct, profile, limits)
    if decision == "BLOCK":
        score -= 100.0
    elif decision == "WARN":
        score -= 10.0
    return {
        "contract_version": CALIBRATION_POLICY_GATE_CONTRACT_VERSION,
        "profile": profile.to_dict(),
        "approvable": bool(approvable),
        "decision": decision,
        "ok": decision != "BLOCK",
        "score": round(score, 6),
        "reason_codes": blockers,
        "warnings": warnings,
        "sample_count": sample_count,
        "metrics": {
            "raw_distribution": raw_distribution,
            "raw_action_pct": raw_action_pct,
            "calibrated_distribution": calibrated_distribution,
            "calibrated_action_pct": action_pct,
            "calibrated_hold_pct": _pct(int(calibrated_distribution.get("HOLD", 0) or 0), sample_count),
            "dominant_action_pct": dominant_action_pct,
            "low_margin_rejection_pct": low_margin_reject_pct,
            "calibration_reason_counts": dict(sorted(reason_counts.items())),
            "raw_margin": _margin_summary(sample_list),
        },
    }


def build_policy_profiles(samples: Sequence[Mapping[str, Any]], *, include_references: bool = True) -> list[tuple[ThresholdProfile, bool]]:
    profiles: list[tuple[ThresholdProfile, bool]] = []
    seen: set[str] = set()
    if include_references:
        for profile in build_threshold_profiles(samples, include_current=True):
            if profile.name not in seen:
                profiles.append((profile, False)); seen.add(profile.name)
    for profile in CALIBRATION_CANDIDATE_PROFILES:
        if profile.name not in seen:
            profiles.append((profile, True)); seen.add(profile.name)
    if include_references and "no_margin_probe" not in seen:
        profiles.append((ThresholdProfile("no_margin_probe", buy_threshold=0.45, sell_threshold=0.45, hold_band_low=0.35, hold_band_high=0.65, indecision_margin=0.0), False))
    return profiles


def build_calibration_policy_gate(samples: Sequence[Mapping[str, Any]], *, limits: CalibrationPolicyGateLimits | None = None, include_references: bool = True) -> dict[str, Any]:
    limits = limits or CalibrationPolicyGateLimits()
    sample_list = [dict(sample) for sample in samples]
    profile_results = [evaluate_calibration_profile(sample_list, profile, limits=limits, approvable=approvable) for profile, approvable in build_policy_profiles(sample_list, include_references=include_references)]
    approvable_results = [r for r in profile_results if r.get("approvable") is True]
    pass_results = sorted([r for r in approvable_results if r.get("decision") == "PASS"], key=lambda r: float(r.get("score") or -9999), reverse=True)
    warn_results = sorted([r for r in approvable_results if r.get("decision") == "WARN"], key=lambda r: float(r.get("score") or -9999), reverse=True)
    ranked_results = sorted(approvable_results, key=lambda r: float(r.get("score") or -9999), reverse=True)
    selected = pass_results[0] if pass_results else (warn_results[0] if warn_results else (ranked_results[0] if ranked_results else None))
    if pass_results:
        decision = "PASS"; approved = True; recommendation = "Use the selected calibration profile only for controlled paper/demo validation after explicit operator approval. Do not enable real live trading."
    elif warn_results:
        decision = "WARN"; approved = False; recommendation = "A candidate exists but has warnings. Review distribution and run longer paper-only validation before applying."
    else:
        decision = "BLOCK"; approved = False; recommendation = "No safe calibration candidate passed the gate. Do not relax thresholds; collect more data or revisit model/feature calibration."
    top_blockers = Counter(reason for result in approvable_results for reason in result.get("reason_codes", []))
    return {
        "contract_version": CALIBRATION_POLICY_GATE_CONTRACT_VERSION,
        "report_type": "calibration_policy_candidate_gate",
        "decision": decision,
        "ok": decision == "PASS",
        "approved_for_paper_candidate": approved,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "observation_only": True,
        "no_post_actions": True,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "sample_count": len(sample_list),
        "limits": limits.to_dict(),
        "recommendation": recommendation,
        "selected_profile": selected,
        "reason_codes": [] if decision == "PASS" else sorted(top_blockers),
        "guardrails": {"observation_only": True, "get_only": True, "post_requests_allowed": False, "config_mutation_performed": False, "order_actions_performed": False, "reload_performed": False, "live_real_allowed": False, "no_margin_probe_approvable": False},
        "profiles": profile_results,
    }


def samples_from_24e_report(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    samples = report.get("samples")
    if isinstance(samples, Sequence) and not isinstance(samples, (str, bytes)):
        return [dict(sample) for sample in samples if isinstance(sample, Mapping)]
    return []
