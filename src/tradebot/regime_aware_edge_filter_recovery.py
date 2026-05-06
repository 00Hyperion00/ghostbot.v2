from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from tradebot.cost_aware_label_policy_recovery import CostAwareLabelPolicyCandidate, default_cost_aware_label_policy_candidates
from tradebot.two_stage_action_side_recovery import (
    TwoStageActionSideCandidateSpec,
    _binary_sample_weights,
    _feature_columns,
    _normalize_ohlcv,
    _prob_positive,
    _safe_f1,
    _safe_precision,
    _safe_recall,
    _thresholds,
    _training_matrix,
    _validate_split_indices,
    _xgb_classifier,
    cost_aware_policy_from_dict,
    select_policies_from_cost_aware_report,
)
from tradebot.training.labeling import build_cost_aware_atr_targets

REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION = "4B.4.3.6.6.24L"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_IDS = (1, 2)


@dataclass(frozen=True, slots=True)
class RegimeEdgeFilterLimits:
    min_clean_samples: int = 1_000
    min_filter_action_count: int = 30
    min_filtered_action_pct: float = 1.0
    max_filtered_action_pct: float = 35.0
    max_filtered_action_side_pct: float = 82.0
    min_action_precision_lift: float = 0.02
    min_action_precision: float = 0.18
    min_side_accuracy: float = 0.54
    min_expected_edge_proxy_bps: float = 1.0
    min_directional_entropy: float = 0.62
    target_filtered_action_pct: float = 12.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RegimeFilterCandidate:
    name: str
    family: str
    description: str
    approvable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return float(parsed)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pct(part: int | float, total: int | float) -> float:
    total_f = float(total or 0.0)
    if total_f <= 0.0:
        return 0.0
    return round((float(part) / total_f) * 100.0, 6)


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _class_distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(v, 0) for v in values)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _dominant_action_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    return _pct(max(buy, sell), total)


def _directional_entropy(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in (buy, sell):
        if count > 0:
            p = count / total
            entropy -= p * log2(p)
    return round(float(entropy), 6)


def _expected_edge_proxy_bps(pred: np.ndarray, actual: np.ndarray, effective_min_profit_bps: float) -> float:
    pred = np.asarray(pred, dtype=int)
    actual = np.asarray(actual, dtype=int)
    action_mask = pred != 0
    if not bool(action_mask.any()):
        return 0.0
    correct = int(((pred == actual) & action_mask).sum())
    incorrect = int(((pred != actual) & action_mask).sum())
    total = int(action_mask.sum())
    return round(float(((correct - incorrect) / max(total, 1)) * float(effective_min_profit_bps)), 6)


def _binary_action_metrics(pred: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    y_true = (np.asarray(actual, dtype=int) != 0).astype(int)
    y_pred = (np.asarray(pred, dtype=int) != 0).astype(int)
    return {
        "action_precision": round(_safe_precision(y_true, y_pred), 8),
        "action_recall": round(_safe_recall(y_true, y_pred), 8),
        "action_f1": round(_safe_f1(y_true, y_pred), 8),
    }


def _side_accuracy(pred: np.ndarray, actual: np.ndarray) -> float:
    pred = np.asarray(pred, dtype=int)
    actual = np.asarray(actual, dtype=int)
    mask = (pred != 0) & (actual != 0)
    if not bool(mask.any()):
        return 0.0
    return round(float((pred[mask] == actual[mask]).mean()), 8)


def _feature(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype("float64")


def _q_bucket(series: pd.Series, q: float, *, high: bool = True) -> pd.Series:
    if series.empty:
        return pd.Series([], dtype=bool)
    threshold = float(series.quantile(q))
    return series >= threshold if high else series <= threshold


def default_regime_filter_candidates() -> list[RegimeFilterCandidate]:
    return [
        RegimeFilterCandidate("all_staged_actions", "diagnostic", "Diagnostic unfiltered staged actions", approvable=False),
        RegimeFilterCandidate("mtf_trend_aligned", "trend", "BUY with positive 15m trend or SELL with negative 15m trend"),
        RegimeFilterCandidate("ema_vwap_aligned", "trend", "Staged side aligned with EMA spread and VWAP distance"),
        RegimeFilterCandidate("high_volume_pressure", "volume", "High volume regime with taker/price pressure alignment"),
        RegimeFilterCandidate("atr_expansion_non_range", "volatility", "ATR expansion while range regime is not dominant"),
        RegimeFilterCandidate("rsi_mid_trend", "momentum", "RSI in non-extreme trend-following band"),
        RegimeFilterCandidate("trend_strength_top_quartile", "trend", "Top-quartile trend strength proxy"),
        RegimeFilterCandidate("vwap_breakout_side", "vwap", "Side agrees with close-to-VWAP sign"),
        RegimeFilterCandidate("low_range_high_trend", "regime", "Low range flag and high trend strength"),
    ]


def _regime_mask(name: str, features: pd.DataFrame, staged_pred: np.ndarray) -> np.ndarray:
    n = len(features)
    staged = np.asarray(staged_pred, dtype=int)
    action = staged != 0
    if name == "all_staged_actions":
        return np.asarray(action, dtype=bool)

    mtf_trend = _feature(features, "mtf_15m_trend_flag")
    mtf_gap = _feature(features, "mtf_15m_ema_gap_pct")
    ema_spread = _feature(features, "ema_spread_pct")
    close_vwap = _feature(features, "close_to_vwap_pct")
    vwap_atr = _feature(features, "vwap_distance_atr_norm")
    volume = _feature(features, "volume")
    atr_pct = _feature(features, "atr_pct")
    range_flag = _feature(features, "range_regime_flag")
    vol_flag = _feature(features, "volatility_regime_flag")
    trend_strength = _feature(features, "trend_strength_proxy")
    rsi = _feature(features, "RSI_14", 50.0)
    close_loc = _feature(features, "close_location_pct", 0.5)

    buy = staged == 1
    sell = staged == 2
    side_positive = buy & ((mtf_trend > 0) | (mtf_gap > 0))
    side_negative = sell & ((mtf_trend < 0) | (mtf_gap < 0))
    if name == "mtf_trend_aligned":
        return np.asarray(action & (side_positive | side_negative), dtype=bool)
    if name == "ema_vwap_aligned":
        buy_aligned = buy & (ema_spread > 0) & (close_vwap >= 0)
        sell_aligned = sell & (ema_spread < 0) & (close_vwap <= 0)
        return np.asarray(action & (buy_aligned | sell_aligned), dtype=bool)
    if name == "high_volume_pressure":
        high_vol = _q_bucket(volume, 0.70, high=True)
        buy_pressure = buy & (close_loc >= 0.55)
        sell_pressure = sell & (close_loc <= 0.45)
        return np.asarray(action & high_vol.to_numpy(dtype=bool) & (buy_pressure | sell_pressure), dtype=bool)
    if name == "atr_expansion_non_range":
        high_atr = _q_bucket(atr_pct, 0.65, high=True)
        non_range = range_flag <= 0
        return np.asarray(action & high_atr.to_numpy(dtype=bool) & non_range.to_numpy(dtype=bool), dtype=bool)
    if name == "rsi_mid_trend":
        buy_ok = buy & rsi.between(45.0, 68.0)
        sell_ok = sell & rsi.between(32.0, 55.0)
        return np.asarray(action & (buy_ok | sell_ok), dtype=bool)
    if name == "trend_strength_top_quartile":
        strong = _q_bucket(trend_strength.abs(), 0.75, high=True)
        return np.asarray(action & strong.to_numpy(dtype=bool), dtype=bool)
    if name == "vwap_breakout_side":
        buy_ok = buy & ((close_vwap > 0) | (vwap_atr > 0))
        sell_ok = sell & ((close_vwap < 0) | (vwap_atr < 0))
        return np.asarray(action & (buy_ok | sell_ok), dtype=bool)
    if name == "low_range_high_trend":
        low_range = range_flag <= 0
        high_trend = _q_bucket(trend_strength.abs(), 0.60, high=True)
        return np.asarray(action & low_range.to_numpy(dtype=bool) & high_trend.to_numpy(dtype=bool), dtype=bool)
    return np.zeros(n, dtype=bool)


def evaluate_regime_filter_candidate(
    *,
    candidate: RegimeFilterCandidate,
    actual: Sequence[int],
    staged_pred: Sequence[int],
    features: pd.DataFrame,
    baseline_action_precision: float,
    effective_min_profit_bps: float,
    limits: RegimeEdgeFilterLimits | None = None,
) -> dict[str, Any]:
    limits = limits or RegimeEdgeFilterLimits()
    actual_arr = np.asarray(actual, dtype=int)
    staged_arr = np.asarray(staged_pred, dtype=int)
    if len(actual_arr) != len(staged_arr):
        raise ValueError("actual and staged_pred length mismatch")
    mask = _regime_mask(candidate.name, features.reset_index(drop=True), staged_arr)
    filtered_pred = np.where(mask, staged_arr, 0).astype(int)
    distribution = _class_distribution(filtered_pred)
    metrics = _binary_action_metrics(filtered_pred, actual_arr)
    side_acc = _side_accuracy(filtered_pred, actual_arr)
    edge = _expected_edge_proxy_bps(filtered_pred, actual_arr, effective_min_profit_bps)
    action_count = int((filtered_pred != 0).sum())
    action_pct = _pct(action_count, len(filtered_pred))
    side_pct = _dominant_action_pct(distribution)
    entropy = _directional_entropy(distribution)
    precision_lift = round(float(metrics["action_precision"] - float(baseline_action_precision or 0.0)), 8)

    reasons: list[str] = []
    warnings: list[str] = []
    if not candidate.approvable:
        _append_unique(reasons, "DIAGNOSTIC_FILTER_NOT_APPROVABLE")
    if len(actual_arr) < limits.min_clean_samples:
        _append_unique(reasons, "REGIME_SAMPLE_COUNT_LOW")
    if action_count < limits.min_filter_action_count:
        _append_unique(reasons, "REGIME_FILTER_ACTION_COUNT_LOW")
    if action_pct < limits.min_filtered_action_pct:
        _append_unique(reasons, "REGIME_FILTER_ACTION_COVERAGE_LOW")
    if action_pct > limits.max_filtered_action_pct:
        _append_unique(reasons, "REGIME_FILTER_ACTION_COVERAGE_HIGH")
    if side_pct > limits.max_filtered_action_side_pct:
        _append_unique(reasons, "REGIME_FILTER_SIDE_IMBALANCE_HIGH")
    if entropy < limits.min_directional_entropy and action_count > 0:
        _append_unique(reasons, "REGIME_FILTER_DIRECTIONAL_ENTROPY_LOW")
    if metrics["action_precision"] < limits.min_action_precision:
        _append_unique(reasons, "REGIME_FILTER_ACTION_PRECISION_LOW")
    if precision_lift < limits.min_action_precision_lift:
        _append_unique(reasons, "REGIME_FILTER_PRECISION_LIFT_LOW")
    if side_acc < limits.min_side_accuracy:
        _append_unique(reasons, "REGIME_FILTER_SIDE_ACCURACY_LOW")
    if edge < limits.min_expected_edge_proxy_bps:
        _append_unique(reasons, "REGIME_FILTER_EXPECTED_EDGE_LOW")
    if 0 < action_pct < (limits.min_filtered_action_pct * 1.5):
        _append_unique(warnings, "REGIME_FILTER_ACTION_COVERAGE_NEAR_FLOOR")

    score = (
        edge * 2.0
        + metrics["action_precision"] * 100.0
        + side_acc * 30.0
        + precision_lift * 80.0
        - abs(action_pct - limits.target_filtered_action_pct) * 0.8
        - max(0.0, side_pct - 55.0) * 0.7
    )
    decision = "PASS" if not reasons else "BLOCK"
    return {
        "contract_version": REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
        "report_type": "regime_edge_filter_candidate_gate",
        "decision": decision,
        "ok": decision == "PASS",
        "approved_for_training_candidate": decision == "PASS",
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "filter": candidate.to_dict(),
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "sample_count": int(len(actual_arr)),
            "filtered_action_count": action_count,
            "filtered_action_pct": round(action_pct, 6),
            "filtered_distribution": distribution,
            "filtered_action_side_pct": round(side_pct, 6),
            "filtered_directional_entropy": entropy,
            "baseline_action_precision": round(float(baseline_action_precision or 0.0), 8),
            "action_precision_lift": precision_lift,
            "filtered_side_accuracy": side_acc,
            "expected_edge_proxy_bps": round(edge, 6),
            **metrics,
        },
        "limits": limits.to_dict(),
        "score": round(float(score), 6),
    }


def select_regime_edge_filter_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best: Mapping[str, Any] | None = None
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        if best is None or _safe_float(item.get("score"), -1e9) > _safe_float(best.get("score"), -1e9):
            best = item
    approved = bool(best and best.get("decision") == "PASS")
    reasons: list[str] = [] if approved else ["NO_REGIME_EDGE_FILTER_CANDIDATE_PASSED"]
    if not approved and best:
        for code in best.get("reason_codes") or []:
            _append_unique(reasons, str(code))
    return {
        "contract_version": REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
        "decision": "PASS" if approved else "BLOCK",
        "approved": approved,
        "reason_codes": reasons,
        "best_candidate": dict(best or {}),
    }


def build_regime_edge_filter_report(candidates: Sequence[Mapping[str, Any]], *, source: str = "unknown", baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:
    normalized = [dict(item) for item in candidates]
    selection = select_regime_edge_filter_candidate(normalized)
    approved = bool(selection.get("approved"))
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
    return {
        "contract_version": REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
        "phase": REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
        "report_type": "regime_aware_edge_filter_recovery",
        "decision": "PASS" if approved else "BLOCK",
        "ok": approved,
        "source": source,
        "candidate_count": len(normalized),
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "reason_codes": list(selection.get("reason_codes") or []),
        "recommendation": (
            "A regime-aware edge filter candidate passed the training-candidate gate. Review manually; do not start paper/live trading."
            if approved
            else "No regime-aware positive-edge filter passed. Revisit regime features, meta-labels, costs, or model objective before promote/reload."
        ),
        "selected_filter": (best.get("filter") or {}).get("name") if isinstance(best.get("filter"), Mapping) else None,
        "selected_score": best.get("score"),
        "selected_filtered_action_pct": best_metrics.get("filtered_action_pct"),
        "selected_action_precision": best_metrics.get("action_precision"),
        "selected_side_accuracy": best_metrics.get("filtered_side_accuracy"),
        "selected_expected_edge_proxy_bps": best_metrics.get("expected_edge_proxy_bps"),
        "baseline": dict(baseline or {}),
        "selection": selection,
        "candidates": normalized,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "promotion_requires_explicit_flag": True,
        },
    }


def _infer_24k_best_baseline(payload: Mapping[str, Any]) -> dict[str, Any]:
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    gate = best.get("candidate_gate") if isinstance(best.get("candidate_gate"), Mapping) else {}
    metrics = gate.get("metrics") if isinstance(gate.get("metrics"), Mapping) else {}
    if not metrics:
        metrics = {
            "validation_action_precision": payload.get("selected_action_precision", 0.0),
            "validation_side_accuracy": payload.get("selected_side_accuracy", 0.0),
            "expected_edge_proxy_bps": payload.get("selected_expected_edge_proxy_bps", 0.0),
            "validation_staged_action_pct": payload.get("selected_staged_action_pct", 0.0),
        }
    return {
        "source_contract_version": payload.get("contract_version"),
        "source_decision": payload.get("decision"),
        "selected_score": payload.get("selected_score"),
        "validation_action_precision": _safe_float(metrics.get("validation_action_precision")),
        "validation_side_accuracy": _safe_float(metrics.get("validation_side_accuracy")),
        "expected_edge_proxy_bps": _safe_float(metrics.get("expected_edge_proxy_bps")),
        "validation_staged_action_pct": _safe_float(metrics.get("validation_staged_action_pct")),
        "reason_codes": list(payload.get("reason_codes") or []),
    }


def build_report_from_two_stage_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _infer_24k_best_baseline(payload)
    # Aggregate 24K reports do not contain per-sample regime features, so this mode is intentionally a guarded diagnostic.
    candidate = {
        "contract_version": REGIME_AWARE_EDGE_FILTER_CONTRACT_VERSION,
        "report_type": "regime_edge_filter_candidate_gate",
        "decision": "BLOCK",
        "ok": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "filter": RegimeFilterCandidate("aggregate_24k_diagnostic", "diagnostic", "Aggregate 24K report lacks per-sample regime features", approvable=False).to_dict(),
        "reason_codes": ["REGIME_SAMPLE_FEATURES_MISSING", "AGGREGATE_REPORT_NOT_APPROVABLE"],
        "warnings": [],
        "metrics": {
            "baseline_action_precision": baseline.get("validation_action_precision", 0.0),
            "baseline_side_accuracy": baseline.get("validation_side_accuracy", 0.0),
            "baseline_expected_edge_proxy_bps": baseline.get("expected_edge_proxy_bps", 0.0),
            "baseline_staged_action_pct": baseline.get("validation_staged_action_pct", 0.0),
        },
        "limits": RegimeEdgeFilterLimits().to_dict(),
        "score": -100.0,
    }
    report = build_regime_edge_filter_report([candidate], source="aggregate_24k_json", baseline=baseline)
    report["recommendation"] = "24K aggregate report is insufficient for regime filtering. Run 24L with market data so per-sample regime features can be evaluated."
    return report


def train_regime_edge_filter_candidates(
    ohlcv: pd.DataFrame,
    spec: TwoStageActionSideCandidateSpec,
    *,
    symbol: str = "ETHUSDT",
    interval: str = "1m",
    days: int = 90,
    limits: RegimeEdgeFilterLimits | None = None,
) -> dict[str, Any]:
    df = _normalize_ohlcv(ohlcv)
    feature_lag = int(spec.feature_lag if spec.feature_lag is not None else 1)
    labeled = build_cost_aware_atr_targets(df, spec.label_policy.to_label_config(), feature_lag=feature_lag)
    feature_columns = _feature_columns()
    x, y = _training_matrix(labeled, feature_columns)
    train_idx, val_idx = _validate_split_indices(y)
    x_train = x.iloc[train_idx]
    x_val = x.iloc[val_idx].reset_index(drop=True)
    y_train_multi = y.iloc[train_idx].to_numpy(dtype=int)
    y_val_multi = y.iloc[val_idx].to_numpy(dtype=int)
    y_train_action = (y_train_multi != 0).astype(int)
    y_val_action = (y_val_multi != 0).astype(int)

    if len(set(y_train_action.tolist())) < 2:
        raise RuntimeError("Action classifier training set has only one class")
    side_train_mask = y_train_multi != 0
    if int(side_train_mask.sum()) < 20:
        raise RuntimeError("Side classifier training set has insufficient action labels")
    y_train_side = (y_train_multi[side_train_mask] == 2).astype(int)
    if len(set(y_train_side.tolist())) < 2:
        raise RuntimeError("Side classifier training set has only one side class")

    action_model = _xgb_classifier(max_depth=spec.max_depth, n_estimators=spec.n_estimators, learning_rate=spec.learning_rate, seed=436624)
    action_model.fit(x_train, y_train_action, sample_weight=_binary_sample_weights(y_train_action, spec.action_profile))
    side_model = _xgb_classifier(max_depth=spec.max_depth, n_estimators=spec.n_estimators, learning_rate=spec.learning_rate, seed=436625)
    side_model.fit(x_train.iloc[np.where(side_train_mask)[0]], y_train_side, sample_weight=_binary_sample_weights(y_train_side, spec.side_profile))

    thresholds = _thresholds(spec.action_threshold_profile, spec.side_margin_profile)
    action_prob = _prob_positive(action_model, x_val)
    action_pred = (action_prob >= thresholds.action_threshold).astype(int)
    side_sell_prob = _prob_positive(side_model, x_val)
    side_margin = np.abs(side_sell_prob - 0.5) * 2.0
    side_pred_multi = np.where(side_sell_prob >= 0.5, 2, 1).astype(int)
    staged_pred = np.where((action_pred == 1) & (side_margin >= thresholds.side_margin_floor), side_pred_multi, 0).astype(int)

    baseline_metrics = _binary_action_metrics(staged_pred, y_val_multi)
    baseline_edge = _expected_edge_proxy_bps(staged_pred, y_val_multi, spec.label_policy.effective_min_profit_bps)
    baseline_distribution = _class_distribution(staged_pred)
    baseline = {
        "symbol": symbol.upper(),
        "interval": interval,
        "days": int(days),
        "candidate_spec": spec.to_dict(),
        "sample_count": int(len(y_val_multi)),
        "validation_staged_distribution": baseline_distribution,
        "validation_staged_action_pct": _pct(int((staged_pred != 0).sum()), len(staged_pred)),
        "validation_action_precision": baseline_metrics["action_precision"],
        "validation_action_recall": baseline_metrics["action_recall"],
        "validation_action_f1": baseline_metrics["action_f1"],
        "validation_side_accuracy": _side_accuracy(staged_pred, y_val_multi),
        "expected_edge_proxy_bps": baseline_edge,
        "action_threshold": thresholds.action_threshold,
        "side_margin_floor": thresholds.side_margin_floor,
    }
    candidates = [
        evaluate_regime_filter_candidate(
            candidate=item,
            actual=y_val_multi,
            staged_pred=staged_pred,
            features=x_val,
            baseline_action_precision=baseline_metrics["action_precision"],
            effective_min_profit_bps=spec.label_policy.effective_min_profit_bps,
            limits=limits,
        )
        for item in default_regime_filter_candidates()
    ]
    return build_regime_edge_filter_report(candidates, source=f"binance:{symbol.upper()}:{interval}:{days}d", baseline=baseline)


def policy_candidates_from_input(payload: Mapping[str, Any], *, limit: int = 3) -> list[CostAwareLabelPolicyCandidate]:
    if str(payload.get("contract_version", "")).endswith("24I") or payload.get("report_type") == "cost_aware_label_policy_recovery":
        return select_policies_from_cost_aware_report(payload, limit=limit)
    # 24K selected candidate spec can be reused when present.
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    spec = best.get("candidate_spec") if isinstance(best.get("candidate_spec"), Mapping) else {}
    label_policy = spec.get("label_policy") if isinstance(spec.get("label_policy"), Mapping) else {}
    if label_policy:
        try:
            return [cost_aware_policy_from_dict(label_policy)]
        except Exception:
            pass
    return select_policies_from_cost_aware_report(payload, limit=limit)
