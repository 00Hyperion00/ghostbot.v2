from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

from tradebot.runtime_calibration_probe import extract_runtime_probability_sample, signal_from_class

PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION = "4B.4.3.6.6.24G"
ACTION_SIGNALS = {"BUY", "SELL"}
ALL_SIGNALS = ("HOLD", "BUY", "SELL")


@dataclass(frozen=True, slots=True)
class ProbabilitySeparationGateConfig:
    min_samples: int = 30
    min_buy_sell_margin_mean: float = 0.015
    min_buy_sell_margin_median: float = 0.010
    min_action_hold_margin_mean: float = 0.060
    max_raw_action_pct: float = 85.0
    min_raw_action_pct: float = 2.0
    max_action_side_pct: float = 80.0
    min_directional_entropy: float = 0.55
    max_low_margin_reject_pct: float = 60.0
    max_current_action_pct: float = 45.0
    min_current_action_pct_for_ready: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pct(part: int | float, total: int | float) -> float:
    if float(total) <= 0:
        return 0.0
    return round((float(part) / float(total)) * 100.0, 6)


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _get_path(data: Any, path: str, default: Any = None) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, Mapping):
            cur = cur.get(part, default)
        else:
            return default
    return cur


def _distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(str(value or "HOLD").upper() for value in values)
    return {signal: int(counts.get(signal, 0)) for signal in ALL_SIGNALS}


def _summary(values: Sequence[float]) -> dict[str, float]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    vals = sorted(vals)
    return {
        "min": round(vals[0], 8),
        "median": round(float(median(vals)), 8),
        "mean": round(float(mean(vals)), 8),
        "max": round(vals[-1], 8),
    }


def _action_pct(distribution: Mapping[str, Any]) -> float:
    buy = int(distribution.get("BUY", 0) or 0)
    sell = int(distribution.get("SELL", 0) or 0)
    hold = int(distribution.get("HOLD", 0) or 0)
    return _pct(buy + sell, buy + sell + hold)


def _dominant_action_pct(distribution: Mapping[str, Any]) -> float:
    buy = int(distribution.get("BUY", 0) or 0)
    sell = int(distribution.get("SELL", 0) or 0)
    action = buy + sell
    if action <= 0:
        return 0.0
    return _pct(max(buy, sell), action)


def _directional_entropy(distribution: Mapping[str, Any]) -> float:
    buy = int(distribution.get("BUY", 0) or 0)
    sell = int(distribution.get("SELL", 0) or 0)
    action = buy + sell
    if action <= 0:
        return 0.0
    p_buy = buy / action
    p_sell = sell / action
    entropy = 0.0
    for p in (p_buy, p_sell):
        if p > 0:
            entropy -= p * log2(p)
    return round(float(entropy), 6)  # already normalized for two classes: max = 1.0


def normalize_probability_sample(raw: Mapping[str, Any], *, sample_index: int = 0) -> dict[str, Any] | None:
    """Normalize either a 24E probability sample or a modern /status payload.

    Returns None when the payload does not contain buy/sell/hold probabilities.
    """
    if not isinstance(raw, Mapping):
        return None
    if "buy_probability" not in raw and "buyProbability" not in raw:
        maybe_status = extract_runtime_probability_sample(raw, sample_index=sample_index)
        if maybe_status is not None:
            raw = maybe_status

    hold = _safe_float(raw.get("hold_probability") or raw.get("holdProbability"))
    buy = _safe_float(raw.get("buy_probability") or raw.get("buyProbability"))
    sell = _safe_float(raw.get("sell_probability") or raw.get("sellProbability"))
    if hold is None or buy is None or sell is None:
        return None

    raw_class = _safe_int(raw.get("raw_predicted_class") or raw.get("rawPredictedClass"))
    if raw_class is None:
        raw_class = max(range(3), key=lambda idx: [hold, buy, sell][idx])
    raw_signal = str(raw.get("raw_signal") or signal_from_class(raw_class)).upper()
    current_signal = str(raw.get("current_signal") or raw.get("calibrated_signal") or "HOLD").upper()
    calibrated_signal = str(raw.get("calibrated_signal") or current_signal).upper()
    calibration_reason = str(raw.get("calibration_reason") or raw.get("calibrationReason") or "UNKNOWN")
    raw_margin = _safe_float(raw.get("raw_margin") or raw.get("rawMargin"), abs(buy - sell))
    top_action_prob = max(buy, sell)
    action_hold_margin = top_action_prob - hold
    return {
        "contract_version": PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION,
        "sample_index": int(raw.get("sample_index", sample_index) or 0),
        "symbol": raw.get("symbol"),
        "model_path": raw.get("model_path") or _get_path(raw, "ai_snapshot.model_path"),
        "raw_predicted_class": int(raw_class),
        "raw_signal": raw_signal,
        "current_signal": current_signal,
        "calibrated_signal": calibrated_signal,
        "calibration_reason": calibration_reason,
        "hold_probability": float(hold),
        "buy_probability": float(buy),
        "sell_probability": float(sell),
        "raw_top_probability": float(_safe_float(raw.get("raw_top_probability") or raw.get("rawTopProbability"), max(hold, buy, sell)) or 0.0),
        "buy_sell_margin": float(abs(buy - sell)),
        "raw_margin": float(raw_margin or 0.0),
        "action_hold_margin": float(action_hold_margin),
        "threshold_trace": dict(raw.get("threshold_trace") or {}) if isinstance(raw.get("threshold_trace"), Mapping) else {},
        "collected_at": raw.get("collected_at"),
    }


def extract_probability_samples_from_payload(payload: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    def handle_item(item: Any, idx: int) -> None:
        normalized = normalize_probability_sample(item, sample_index=idx) if isinstance(item, Mapping) else None
        if normalized is None:
            rejected.append({"sample_index": idx, "reason": "PROBABILITY_SAMPLE_MISSING"})
        else:
            samples.append(normalized)

    if isinstance(payload, list):
        for idx, item in enumerate(payload):
            handle_item(item, idx)
        return samples, rejected

    if not isinstance(payload, Mapping):
        return [], [{"sample_index": 0, "reason": "UNSUPPORTED_PAYLOAD"}]

    direct = normalize_probability_sample(payload, sample_index=0)
    if direct is not None:
        return [direct], []

    for key in ("samples", "probability_samples", "statuses", "status_payloads"):
        value = payload.get(key)
        if isinstance(value, list):
            for idx, item in enumerate(value):
                handle_item(item, idx)
            return samples, rejected

    # 24F reports intentionally contain only aggregate profile metrics. They are useful
    # context, but insufficient for a probability separation gate because the sample-level
    # buy/sell margins are not replayable.
    if payload.get("report_type") == "calibration_policy_candidate_gate":
        return [], [{"sample_index": 0, "reason": "AGGREGATED_24F_REPORT_REQUIRES_24E_SAMPLE_REPORT"}]

    return [], [{"sample_index": 0, "reason": "NO_PROBABILITY_SAMPLE_ARRAY_FOUND"}]


def _distribution_from_training(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    out = {"0": 0, "1": 0, "2": 0}
    for key, raw_count in value.items():
        count = _safe_int(raw_count, 0) or 0
        if str(key) in out:
            out[str(key)] = max(0, int(count))
    return out


def _rates_from_distribution(counts: Mapping[str, int] | None) -> dict[str, float]:
    counts = counts or {"0": 0, "1": 0, "2": 0}
    total = sum(int(counts.get(k, 0) or 0) for k in ("0", "1", "2"))
    if total <= 0:
        return {"0": 0.0, "1": 0.0, "2": 0.0}
    return {key: round(float(counts.get(key, 0) or 0) / float(total), 8) for key in ("0", "1", "2")}


def build_label_calibration_report(training_result: Mapping[str, Any] | None) -> dict[str, Any]:
    result = dict(training_result or {})
    target = _distribution_from_training(
        result.get("target_distribution")
        or result.get("raw_target_distribution")
        or result.get("training_target_distribution")
    )
    actual = _distribution_from_training(result.get("validation_actual_class_distribution"))
    predicted = _distribution_from_training(result.get("validation_predicted_class_distribution"))
    calibrated = _distribution_from_training(result.get("calibrated_predicted_class_distribution"))
    target_rates = _rates_from_distribution(target)
    predicted_rates = _rates_from_distribution(predicted)
    calibrated_rates = _rates_from_distribution(calibrated)
    warnings: list[str] = []
    reasons: list[str] = []
    if target is None:
        _append_unique(reasons, "LABEL_TARGET_DISTRIBUTION_MISSING")
    if predicted is None and calibrated is None:
        _append_unique(warnings, "VALIDATION_PREDICTION_DISTRIBUTION_MISSING")

    target_action_rate = 1.0 - float(target_rates.get("0", 0.0))
    predicted_action_rate = 1.0 - float(predicted_rates.get("0", 0.0))
    calibrated_action_rate = 1.0 - float(calibrated_rates.get("0", 0.0))
    target_side_total = float(target_rates.get("1", 0.0) + target_rates.get("2", 0.0))
    target_buy_side_pct = 0.0 if target_side_total <= 0 else float(target_rates.get("1", 0.0)) / target_side_total
    if target_side_total > 0 and (target_buy_side_pct > 0.8 or target_buy_side_pct < 0.2):
        _append_unique(warnings, "LABEL_SIDE_IMBALANCE_ELEVATED")

    return {
        "contract_version": PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION,
        "report_type": "label_calibration",
        "decision": "BLOCK" if reasons else ("WARN" if warnings else "PASS"),
        "ok": not reasons,
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "target_distribution": target,
            "target_rates": target_rates,
            "validation_actual_distribution": actual,
            "validation_predicted_distribution": predicted,
            "calibrated_predicted_distribution": calibrated,
            "predicted_rates": predicted_rates,
            "calibrated_rates": calibrated_rates,
            "target_action_rate": round(target_action_rate, 8),
            "predicted_action_rate": round(predicted_action_rate, 8),
            "calibrated_action_rate": round(calibrated_action_rate, 8),
            "target_buy_side_pct": round(target_buy_side_pct, 8),
            "synthetic_class_padding_applied": bool(result.get("synthetic_class_padding_applied", False)),
        },
    }


def build_probability_separation_gate(
    samples: Sequence[Mapping[str, Any]],
    *,
    config: ProbabilitySeparationGateConfig | None = None,
    label_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or ProbabilitySeparationGateConfig()
    normalized = [sample for idx, item in enumerate(samples) if (sample := normalize_probability_sample(item, sample_index=idx)) is not None]
    sample_count = len(normalized)
    raw_distribution = _distribution(sample.get("raw_signal") for sample in normalized)
    current_distribution = _distribution(sample.get("calibrated_signal") or sample.get("current_signal") for sample in normalized)
    calibration_reasons = Counter(str(sample.get("calibration_reason") or "UNKNOWN") for sample in normalized)
    buy_sell_margins = [float(sample.get("buy_sell_margin") or sample.get("raw_margin") or 0.0) for sample in normalized]
    action_hold_margins = [float(sample.get("action_hold_margin") or 0.0) for sample in normalized]
    raw_action_pct = _action_pct(raw_distribution)
    current_action_pct = _action_pct(current_distribution)
    dominant_action_pct = _dominant_action_pct(raw_distribution)
    entropy = _directional_entropy(raw_distribution)
    low_margin_reject_pct = _pct(int(calibration_reasons.get("REJECT_LOW_MARGIN", 0)), sample_count)
    buy_sell_summary = _summary(buy_sell_margins)
    action_hold_summary = _summary(action_hold_margins)

    reasons: list[str] = []
    warnings: list[str] = []
    if sample_count < cfg.min_samples:
        _append_unique(reasons, "SEPARATION_SAMPLE_COUNT_LOW")
    if raw_action_pct < cfg.min_raw_action_pct:
        _append_unique(reasons, "RAW_ACTION_COVERAGE_LOW")
    if raw_action_pct > cfg.max_raw_action_pct:
        _append_unique(reasons, "RAW_ACTION_COVERAGE_TOO_HIGH")
    if float(buy_sell_summary.get("mean", 0.0)) < cfg.min_buy_sell_margin_mean:
        _append_unique(reasons, "BUY_SELL_SEPARATION_MEAN_LOW")
    if float(buy_sell_summary.get("median", 0.0)) < cfg.min_buy_sell_margin_median:
        _append_unique(reasons, "BUY_SELL_SEPARATION_MEDIAN_LOW")
    if float(action_hold_summary.get("mean", 0.0)) < cfg.min_action_hold_margin_mean:
        _append_unique(warnings, "ACTION_VS_HOLD_MARGIN_LOW")
    if dominant_action_pct > cfg.max_action_side_pct:
        _append_unique(reasons, "RAW_ACTION_SIDE_IMBALANCE_HIGH")
    elif dominant_action_pct > 70.0:
        _append_unique(warnings, "RAW_ACTION_SIDE_IMBALANCE_ELEVATED")
    if entropy < cfg.min_directional_entropy and raw_action_pct > 0.0:
        _append_unique(reasons, "DIRECTIONAL_ENTROPY_LOW")
    if low_margin_reject_pct > cfg.max_low_margin_reject_pct:
        _append_unique(reasons, "LOW_MARGIN_REJECTION_HIGH")
    if current_action_pct <= 0.0:
        _append_unique(warnings, "CURRENT_CALIBRATION_ACTION_COVERAGE_ZERO")
    elif current_action_pct < cfg.min_current_action_pct_for_ready:
        _append_unique(warnings, "CURRENT_CALIBRATION_ACTION_COVERAGE_LOW")
    if current_action_pct > cfg.max_current_action_pct:
        _append_unique(reasons, "CURRENT_CALIBRATION_ACTION_COVERAGE_TOO_HIGH")

    decision = "BLOCK" if reasons else ("WARN" if warnings else "PASS")
    if "BUY_SELL_SEPARATION_MEAN_LOW" in reasons or "BUY_SELL_SEPARATION_MEDIAN_LOW" in reasons:
        recommendation = "Do not loosen thresholds yet; improve label horizon, class objective, or feature separation so BUY/SELL probabilities separate before paper trading."
    elif "RAW_ACTION_COVERAGE_TOO_HIGH" in reasons:
        recommendation = "Raw model over-triggers actions. Revisit label calibration/objective before threshold relaxation."
    elif decision == "PASS":
        recommendation = "Probability separation is acceptable for a controlled paper-only candidate gate; live real remains blocked."
    else:
        recommendation = "Review warnings and collect additional samples before selecting a calibration policy."

    return {
        "contract_version": PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION,
        "report_type": "probability_separation_gate",
        "decision": decision,
        "ok": decision != "BLOCK",
        "approved_for_paper_candidate": decision == "PASS",
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reason_codes": reasons,
        "warnings": warnings,
        "recommendation": recommendation,
        "sample_count": sample_count,
        "limits": cfg.to_dict(),
        "metrics": {
            "raw_distribution": raw_distribution,
            "raw_action_pct": raw_action_pct,
            "current_distribution": current_distribution,
            "current_action_pct": current_action_pct,
            "calibration_reason_counts": dict(sorted(calibration_reasons.items())),
            "low_margin_rejection_pct": low_margin_reject_pct,
            "raw_action_side_pct": dominant_action_pct,
            "directional_entropy": entropy,
            "buy_sell_margin": buy_sell_summary,
            "action_vs_hold_margin": action_hold_summary,
        },
        "label_calibration": dict(label_report or {}),
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "reload_performed": False,
            "order_actions_performed": False,
            "live_real_allowed": False,
        },
    }


def build_probability_separation_recovery(
    *,
    samples: Sequence[Mapping[str, Any]] | None = None,
    training_result: Mapping[str, Any] | None = None,
    rejected_samples: Sequence[Mapping[str, Any]] | None = None,
    config: ProbabilitySeparationGateConfig | None = None,
) -> dict[str, Any]:
    label_report = build_label_calibration_report(training_result) if training_result is not None else {}
    gate = build_probability_separation_gate(samples or [], config=config, label_report=label_report)
    gate["phase"] = PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION
    gate["rejected_samples"] = list(rejected_samples or [])
    if training_result is not None:
        gate["training_context"] = {
            "model_path": training_result.get("model_path") or training_result.get("output"),
            "class_weight_profile": training_result.get("class_weight_profile"),
            "threshold_profile": training_result.get("threshold_profile"),
            "days": training_result.get("days"),
            "feature_lag": training_result.get("feature_lag"),
        }
    return gate
