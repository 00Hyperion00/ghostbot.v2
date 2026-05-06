from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from tradebot.features import FEATURE_COLUMNS, clean_feature_frame
from tradebot.training.labeling import ATRLabelConfig, build_cost_aware_atr_targets

LABEL_HORIZON_RECOVERY_CONTRACT_VERSION = "4B.4.3.6.6.24H"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
TARGET_KEYS = ("HOLD", "BUY", "SELL")


@dataclass(frozen=True, slots=True)
class LabelPolicyCandidate:
    name: str
    lookahead: int
    atr_multiplier: float
    min_profit_bps: float = 0.0
    use_high_low_barriers: bool = True
    ambiguous_barrier_policy: str = "hold"
    approvable: bool = True
    family: str = "candidate"

    def to_label_config(self) -> ATRLabelConfig:
        return ATRLabelConfig(
            lookahead=int(self.lookahead),
            atr_multiplier=float(self.atr_multiplier),
            min_profit_bps=float(self.min_profit_bps),
            use_high_low_barriers=bool(self.use_high_low_barriers),
            ambiguous_barrier_policy=str(self.ambiguous_barrier_policy or "hold"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LabelHorizonGateLimits:
    min_samples: int = 1000
    min_action_pct: float = 3.0
    max_action_pct: float = 45.0
    min_hold_pct: float = 35.0
    max_hold_pct: float = 92.0
    max_action_side_pct: float = 78.0
    min_directional_entropy: float = 0.68
    min_forward_return_gap_bps: float = 8.0
    min_buy_direction_consistency_pct: float = 55.0
    min_sell_direction_consistency_pct: float = 55.0
    min_class_count: int = 20
    target_action_pct: float = 18.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if pd.isna(out):
        return default
    return out


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


def _summary(values: Sequence[float]) -> dict[str, float]:
    vals = sorted(float(v) for v in values if v is not None and not pd.isna(v))
    if not vals:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": round(vals[0], 8),
        "median": round(float(median(vals)), 8),
        "mean": round(float(mean(vals)), 8),
        "max": round(vals[-1], 8),
    }


def _target_distribution(targets: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(value, 0) for value in targets)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _action_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    hold = _safe_int(distribution.get("HOLD"), 0)
    return _pct(buy + sell, buy + sell + hold)


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


def default_label_policy_candidates() -> list[LabelPolicyCandidate]:
    return [
        LabelPolicyCandidate("current_baseline_h10_atr1_5", 10, 1.5, approvable=False, family="baseline"),
        LabelPolicyCandidate("h3_atr0_8_fast", 3, 0.8, family="fast"),
        LabelPolicyCandidate("h5_atr0_9_fast_balanced", 5, 0.9, family="fast"),
        LabelPolicyCandidate("h5_atr1_1_balanced", 5, 1.1, family="balanced"),
        LabelPolicyCandidate("h10_atr1_0_balanced", 10, 1.0, family="balanced"),
        LabelPolicyCandidate("h10_atr1_25_balanced", 10, 1.25, family="balanced"),
        LabelPolicyCandidate("h15_atr1_25_directional", 15, 1.25, family="directional"),
        LabelPolicyCandidate("h15_atr1_5_directional", 15, 1.5, family="directional"),
        LabelPolicyCandidate("h20_atr1_5_directional_strong", 20, 1.5, family="directional_strong"),
        LabelPolicyCandidate("h20_atr1_8_directional_strong", 20, 1.8, family="directional_strong"),
    ]


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {
        "openTime": "open_time",
        "closeTime": "close_time",
        "quoteVolume": "quote_volume",
    }
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values("close_time" if "close_time" in out.columns else "open_time").reset_index(drop=True)


def _forward_return_bps(labeled: pd.DataFrame, lookahead: int) -> pd.Series:
    close = pd.to_numeric(labeled.get("close"), errors="coerce")
    future = close.shift(-max(int(lookahead), 1))
    ret = ((future / close.replace(0.0, pd.NA)) - 1.0) * 10_000.0
    return pd.to_numeric(ret, errors="coerce")


def _direction_consistency_pct(returns: pd.Series, *, side: str) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    if side.upper() == "BUY":
        return _pct(int((clean > 0.0).sum()), int(len(clean)))
    if side.upper() == "SELL":
        return _pct(int((clean < 0.0).sum()), int(len(clean)))
    return 0.0


def analyze_label_policy(
    df: pd.DataFrame,
    policy: LabelPolicyCandidate,
    *,
    limits: LabelHorizonGateLimits | None = None,
    feature_lag: int = 1,
) -> dict[str, Any]:
    limits = limits or LabelHorizonGateLimits()
    source = _normalize_ohlcv(df)
    reason_codes: list[str] = []
    warnings: list[str] = []

    if source.empty:
        return {
            "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
            "policy": policy.to_dict(),
            "decision": "BLOCK",
            "ok": False,
            "approvable": bool(policy.approvable),
            "sample_count": 0,
            "clean_samples": 0,
            "reason_codes": ["OHLCV_DATA_EMPTY", "LABEL_SAMPLE_COUNT_LOW"],
            "warnings": [],
            "metrics": {},
            "score": -999.0,
        }

    try:
        labeled = build_cost_aware_atr_targets(source, config=policy.to_label_config(), feature_lag=int(feature_lag))
    except Exception as exc:
        return {
            "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
            "policy": policy.to_dict(),
            "decision": "BLOCK",
            "ok": False,
            "approvable": bool(policy.approvable),
            "sample_count": 0,
            "clean_samples": 0,
            "reason_codes": ["LABEL_POLICY_BUILD_FAILED"],
            "warnings": [str(exc)[:500]],
            "metrics": {},
            "score": -999.0,
        }

    sample_count = int(len(labeled))
    try:
        clean_samples = int(len(clean_feature_frame(labeled, require_target=True, feature_columns=FEATURE_COLUMNS)))
    except Exception:
        clean_samples = sample_count

    targets = labeled["target"] if "target" in labeled.columns else pd.Series(dtype="int64")
    dist = _target_distribution(targets)
    total = sum(dist.values())
    action_pct = _action_pct(dist)
    hold_pct = _pct(dist.get("HOLD", 0), total)
    dominant_action_pct = _dominant_action_pct(dist)
    entropy = _directional_entropy(dist)

    fwd = _forward_return_bps(labeled, policy.lookahead)
    buy_returns = fwd[targets.astype("int64", errors="ignore") == 1] if sample_count > 0 else pd.Series(dtype="float64")
    sell_returns = fwd[targets.astype("int64", errors="ignore") == 2] if sample_count > 0 else pd.Series(dtype="float64")
    buy_ret_clean = pd.to_numeric(buy_returns, errors="coerce").dropna()
    sell_ret_clean = pd.to_numeric(sell_returns, errors="coerce").dropna()
    buy_mean = float(buy_ret_clean.mean()) if not buy_ret_clean.empty else 0.0
    sell_mean = float(sell_ret_clean.mean()) if not sell_ret_clean.empty else 0.0
    forward_gap = float(buy_mean - sell_mean)
    buy_consistency = _direction_consistency_pct(buy_ret_clean, side="BUY")
    sell_consistency = _direction_consistency_pct(sell_ret_clean, side="SELL")

    if sample_count < limits.min_samples:
        _append_unique(reason_codes, "LABEL_SAMPLE_COUNT_LOW")
    if clean_samples < limits.min_samples:
        _append_unique(reason_codes, "LABEL_CLEAN_SAMPLE_COUNT_LOW")
    if dist.get("BUY", 0) < limits.min_class_count or dist.get("SELL", 0) < limits.min_class_count:
        _append_unique(reason_codes, "TARGET_ACTION_CLASS_COVERAGE_LOW")
    if action_pct < limits.min_action_pct:
        _append_unique(reason_codes, "TARGET_ACTION_COVERAGE_LOW")
    if action_pct > limits.max_action_pct:
        _append_unique(reason_codes, "TARGET_ACTION_COVERAGE_HIGH")
    if hold_pct < limits.min_hold_pct:
        _append_unique(reason_codes, "TARGET_HOLD_COVERAGE_LOW")
    if hold_pct > limits.max_hold_pct:
        _append_unique(reason_codes, "TARGET_HOLD_DOMINANCE_HIGH")
    if dominant_action_pct > limits.max_action_side_pct:
        _append_unique(reason_codes, "TARGET_ACTION_SIDE_IMBALANCE_HIGH")
    if entropy < limits.min_directional_entropy:
        _append_unique(reason_codes, "TARGET_DIRECTIONAL_ENTROPY_LOW")
    if forward_gap < limits.min_forward_return_gap_bps:
        _append_unique(reason_codes, "FORWARD_RETURN_SEPARATION_LOW")
    if buy_consistency < limits.min_buy_direction_consistency_pct:
        _append_unique(reason_codes, "BUY_DIRECTION_CONSISTENCY_LOW")
    if sell_consistency < limits.min_sell_direction_consistency_pct:
        _append_unique(reason_codes, "SELL_DIRECTION_CONSISTENCY_LOW")
    if not policy.approvable:
        _append_unique(reason_codes, "DIAGNOSTIC_POLICY_NOT_APPROVABLE")

    # Useful but not hard blockers: they tell the next training sweep how close a policy is.
    if action_pct > 0 and abs(action_pct - limits.target_action_pct) <= 5.0:
        warnings.append("TARGET_ACTION_RATE_NEAR_TARGET")
    if limits.max_action_side_pct - 5.0 < dominant_action_pct <= limits.max_action_side_pct:
        warnings.append("TARGET_ACTION_SIDE_IMBALANCE_ELEVATED")

    ok = bool(policy.approvable) and not reason_codes
    decision = "PASS" if ok else "BLOCK"
    # Score favors clean separation, action rate near target, class balance and consistency.
    score = 0.0
    score += min(forward_gap, 50.0) / 5.0
    score += entropy * 8.0
    score += max(0.0, 20.0 - abs(action_pct - limits.target_action_pct)) / 2.0
    score += min(buy_consistency, sell_consistency) / 20.0
    score -= max(0.0, dominant_action_pct - 50.0) / 2.5
    score -= max(0.0, action_pct - limits.max_action_pct) * 2.0
    score -= max(0.0, limits.min_action_pct - action_pct) * 2.0
    score -= len(reason_codes) * 8.0
    if not policy.approvable:
        score -= 4.0

    metrics = {
        "target_distribution": dist,
        "target_action_pct": round(action_pct, 6),
        "target_hold_pct": round(hold_pct, 6),
        "target_action_side_pct": round(dominant_action_pct, 6),
        "directional_entropy": round(entropy, 6),
        "forward_return_gap_bps": round(forward_gap, 6),
        "buy_forward_return_bps": _summary(buy_ret_clean.tolist()),
        "sell_forward_return_bps": _summary(sell_ret_clean.tolist()),
        "buy_direction_consistency_pct": round(buy_consistency, 6),
        "sell_direction_consistency_pct": round(sell_consistency, 6),
        "label_config": policy.to_label_config().to_dict() | {"feature_lag": int(feature_lag)},
    }
    return {
        "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
        "policy": policy.to_dict(),
        "decision": decision,
        "ok": ok,
        "approvable": bool(policy.approvable),
        "sample_count": sample_count,
        "clean_samples": clean_samples,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "metrics": metrics,
        "score": round(float(score), 6),
    }


def select_best_label_policy(evaluations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ranked = sorted(evaluations, key=lambda item: float(item.get("score") or -999.0), reverse=True)
    passing = [item for item in ranked if item.get("decision") == "PASS" and bool(item.get("approvable"))]
    if passing:
        return {
            "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
            "decision": "PASS",
            "approved": True,
            "reason_codes": [],
            "selected_policy": dict(passing[0]),
            "pass_count": len(passing),
            "candidate_count": len(evaluations),
        }
    reason_codes: list[str] = []
    for item in ranked:
        for code in item.get("reason_codes") or []:
            _append_unique(reason_codes, str(code))
    return {
        "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
        "decision": "BLOCK",
        "approved": False,
        "reason_codes": reason_codes,
        "selected_policy": dict(ranked[0]) if ranked else None,
        "pass_count": 0,
        "candidate_count": len(evaluations),
    }


def build_label_horizon_recovery(
    df: pd.DataFrame,
    *,
    policies: Sequence[LabelPolicyCandidate] | None = None,
    limits: LabelHorizonGateLimits | None = None,
    feature_lag: int = 1,
    source: str | None = None,
) -> dict[str, Any]:
    limits = limits or LabelHorizonGateLimits()
    candidate_policies = list(policies or default_label_policy_candidates())
    source_df = _normalize_ohlcv(df)
    evaluations = [analyze_label_policy(source_df, policy, limits=limits, feature_lag=feature_lag) for policy in candidate_policies]
    selection = select_best_label_policy(evaluations)
    approved = bool(selection.get("approved"))
    decision = "PASS" if approved else "BLOCK"
    selected = selection.get("selected_policy") if isinstance(selection.get("selected_policy"), Mapping) else None
    return {
        "contract_version": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
        "phase": LABEL_HORIZON_RECOVERY_CONTRACT_VERSION,
        "report_type": "label_horizon_target_engineering_recovery",
        "source": source,
        "decision": decision,
        "ok": approved,
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "observation_only": True,
        "no_post_actions": True,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "guardrails": {
            "observation_only": True,
            "get_only_public_market_data": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
        },
        "limits": limits.to_dict(),
        "sample_count": int(len(source_df)),
        "policy_count": len(evaluations),
        "selected_policy_name": (selected or {}).get("policy", {}).get("name") if selected else None,
        "selected_policy": selected,
        "policies": evaluations,
        "selection": selection,
        "reason_codes": list(selection.get("reason_codes") or []),
        "recommendation": (
            "A label policy candidate passed the training-candidate gate. Use it only for a controlled retrain sweep; do not start paper/live trading yet."
            if approved
            else "No safe label horizon / target policy passed. Revisit horizon, ATR multiplier, costs, or feature separation before retraining."
        ),
    }


__all__ = [
    "LABEL_HORIZON_RECOVERY_CONTRACT_VERSION",
    "LabelPolicyCandidate",
    "LabelHorizonGateLimits",
    "default_label_policy_candidates",
    "analyze_label_policy",
    "select_best_label_policy",
    "build_label_horizon_recovery",
]
