from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from tradebot.training.labeling import ATRLabelConfig, build_cost_aware_atr_targets

MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION = "4B.4.3.6.6.25A"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}


@dataclass(frozen=True, slots=True)
class MultiTimeframeAlphaCandidate:
    name: str
    interval: str
    lookahead: int
    atr_multiplier: float
    cost_bps: float
    min_edge_bps: float
    family: str = "mtf_alpha"
    approvable: bool = True
    use_high_low_barriers: bool = True
    ambiguous_barrier_policy: str = "hold"

    @property
    def effective_min_profit_bps(self) -> float:
        return float(self.cost_bps + self.min_edge_bps)

    def to_label_config(self) -> ATRLabelConfig:
        cost = float(self.cost_bps)
        return ATRLabelConfig(
            lookahead=int(self.lookahead),
            atr_multiplier=float(self.atr_multiplier),
            entry_fee_bps=cost / 4.0,
            exit_fee_bps=cost / 4.0,
            entry_slippage_bps=cost / 4.0,
            exit_slippage_bps=cost / 4.0,
            min_profit_bps=float(self.effective_min_profit_bps),
            use_high_low_barriers=bool(self.use_high_low_barriers),
            ambiguous_barrier_policy=str(self.ambiguous_barrier_policy or "hold"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["effective_min_profit_bps"] = round(float(self.effective_min_profit_bps), 6)
        return payload


@dataclass(frozen=True, slots=True)
class MultiTimeframeAlphaGateLimits:
    min_samples: int = 600
    min_action_pct: float = 4.0
    max_action_pct: float = 42.0
    min_hold_pct: float = 45.0
    max_action_side_pct: float = 76.0
    min_directional_entropy: float = 0.70
    min_forward_return_gap_bps: float = 10.0
    min_expected_net_edge_bps: float = 1.0
    min_trend_alignment_pct: float = 50.0
    min_feature_separation_score: float = 0.0
    min_class_count: int = 20
    target_action_pct: float = 18.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if pd.isna(out):
            return default
        return out
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


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"openTime": "open_time", "closeTime": "close_time", "quoteVolume": "quote_volume"}
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    sort_col = "close_time" if "close_time" in out.columns else "open_time"
    return out.sort_values(sort_col).reset_index(drop=True)


def _forward_return_bps(frame: pd.DataFrame, lookahead: int) -> pd.Series:
    close = pd.to_numeric(frame.get("close"), errors="coerce")
    future = close.shift(-max(int(lookahead), 1))
    ret = ((future / close.replace(0.0, pd.NA)) - 1.0) * 10_000.0
    return pd.to_numeric(ret, errors="coerce")


def _trend_alignment_pct(labeled: pd.DataFrame, targets: pd.Series) -> float:
    if labeled.empty:
        return 0.0
    ema_fast = pd.to_numeric(labeled.get("EMA_9"), errors="coerce")
    ema_slow = pd.to_numeric(labeled.get("EMA_21"), errors="coerce")
    buy_mask = targets == 1
    sell_mask = targets == 2
    action_mask = buy_mask | sell_mask
    total = int(action_mask.sum())
    if total <= 0:
        return 0.0
    aligned = int(((buy_mask & (ema_fast > ema_slow)) | (sell_mask & (ema_fast < ema_slow))).sum())
    return _pct(aligned, total)


def _feature_separation_score(labeled: pd.DataFrame, targets: pd.Series) -> float:
    if labeled.empty:
        return 0.0
    trend = pd.to_numeric(labeled.get("trend_strength_proxy"), errors="coerce").fillna(0.0).abs()
    vwap = pd.to_numeric(labeled.get("vwap_distance_atr_norm"), errors="coerce").fillna(0.0).abs()
    ema = pd.to_numeric(labeled.get("ema_spread_pct"), errors="coerce").fillna(0.0).abs()
    action = targets.isin([1, 2])
    hold = targets == 0
    if int(action.sum()) <= 0 or int(hold.sum()) <= 0:
        return 0.0
    action_strength = float((trend[action].mean() + vwap[action].mean() + ema[action].mean()) / 3.0)
    hold_strength = float((trend[hold].mean() + vwap[hold].mean() + ema[hold].mean()) / 3.0)
    return round(action_strength - hold_strength, 8)


def default_multitimeframe_alpha_candidates() -> list[MultiTimeframeAlphaCandidate]:
    return [
        MultiTimeframeAlphaCandidate("diagnostic_1m_cost16_edge30_atr3_0", "1m", 30, 3.0, cost_bps=16.0, min_edge_bps=30.0, family="diagnostic_1m", approvable=False),
        MultiTimeframeAlphaCandidate("mtf_5m_h12_cost16_edge25_atr2_5", "5m", 12, 2.5, cost_bps=16.0, min_edge_bps=25.0, family="5m_directional"),
        MultiTimeframeAlphaCandidate("mtf_5m_h24_cost16_edge35_atr3_0", "5m", 24, 3.0, cost_bps=16.0, min_edge_bps=35.0, family="5m_slow"),
        MultiTimeframeAlphaCandidate("mtf_15m_h8_cost16_edge30_atr2_5", "15m", 8, 2.5, cost_bps=16.0, min_edge_bps=30.0, family="15m_directional"),
        MultiTimeframeAlphaCandidate("mtf_15m_h16_cost20_edge40_atr3_0", "15m", 16, 3.0, cost_bps=20.0, min_edge_bps=40.0, family="15m_slow"),
        MultiTimeframeAlphaCandidate("mtf_1h_h6_cost20_edge50_atr2_5", "1h", 6, 2.5, cost_bps=20.0, min_edge_bps=50.0, family="1h_directional"),
        MultiTimeframeAlphaCandidate("mtf_1h_h12_cost20_edge70_atr3_0", "1h", 12, 3.0, cost_bps=20.0, min_edge_bps=70.0, family="1h_swing"),
    ]


def analyze_multitimeframe_alpha_candidate(
    df: pd.DataFrame,
    candidate: MultiTimeframeAlphaCandidate,
    *,
    limits: MultiTimeframeAlphaGateLimits | None = None,
    source: str | None = None,
    feature_lag: int = 1,
) -> dict[str, Any]:
    limits = limits or MultiTimeframeAlphaGateLimits()
    reason_codes: list[str] = []
    warnings: list[str] = []
    normalized = _normalize_ohlcv(df)
    try:
        labeled = build_cost_aware_atr_targets(normalized, candidate.to_label_config(), feature_lag=feature_lag)
    except Exception as exc:
        return {
            "contract_version": MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
            "report_type": "multitimeframe_alpha_candidate_gate",
            "decision": "BLOCK",
            "ok": False,
            "candidate": candidate.to_dict(),
            "source": source,
            "sample_count": 0,
            "reason_codes": ["MTF_LABEL_BUILD_FAILED"],
            "warnings": [str(exc)],
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "live_real_allowed": False,
            "score": -999.0,
        }

    sample_count = int(len(labeled))
    targets = pd.to_numeric(labeled.get("target"), errors="coerce").fillna(0).astype(int)
    dist = _target_distribution(targets)
    action_pct = _action_pct(dist)
    hold_pct = _pct(dist.get("HOLD", 0), sum(dist.values()))
    side_pct = _dominant_action_pct(dist)
    entropy = _directional_entropy(dist)
    fwd = _forward_return_bps(labeled, int(candidate.lookahead))
    buy_returns = fwd[targets == 1].dropna()
    sell_returns = (-fwd[targets == 2]).dropna()
    hold_abs_returns = fwd[targets == 0].abs().dropna()
    buy_mean = float(buy_returns.mean()) if not buy_returns.empty else 0.0
    sell_mean = float(sell_returns.mean()) if not sell_returns.empty else 0.0
    action_edge = float(pd.concat([buy_returns, sell_returns]).mean()) if (len(buy_returns) + len(sell_returns)) else 0.0
    hold_abs_mean = float(hold_abs_returns.mean()) if not hold_abs_returns.empty else 0.0
    forward_gap = float(action_edge - hold_abs_mean)
    min_expected_edge = float(min(buy_mean, sell_mean) - candidate.effective_min_profit_bps) if buy_returns.any() and sell_returns.any() else 0.0
    trend_alignment = _trend_alignment_pct(labeled, targets)
    feature_sep = _feature_separation_score(labeled, targets)

    if sample_count < int(limits.min_samples):
        _append_unique(reason_codes, "MTF_SAMPLE_COUNT_LOW")
    if action_pct < float(limits.min_action_pct):
        _append_unique(reason_codes, "MTF_TARGET_ACTION_COVERAGE_LOW")
    if action_pct > float(limits.max_action_pct):
        _append_unique(reason_codes, "MTF_TARGET_ACTION_COVERAGE_HIGH")
    if hold_pct < float(limits.min_hold_pct):
        _append_unique(reason_codes, "MTF_TARGET_HOLD_COVERAGE_LOW")
    if side_pct > float(limits.max_action_side_pct):
        _append_unique(reason_codes, "MTF_TARGET_ACTION_SIDE_IMBALANCE_HIGH")
    if entropy < float(limits.min_directional_entropy):
        _append_unique(reason_codes, "MTF_DIRECTIONAL_ENTROPY_LOW")
    if min(_safe_int(dist.get("BUY")), _safe_int(dist.get("SELL"))) < int(limits.min_class_count):
        _append_unique(reason_codes, "MTF_TARGET_ACTION_CLASS_COUNT_LOW")
    if forward_gap < float(limits.min_forward_return_gap_bps):
        _append_unique(reason_codes, "MTF_FORWARD_RETURN_SEPARATION_LOW")
    if min_expected_edge < float(limits.min_expected_net_edge_bps):
        _append_unique(reason_codes, "MTF_EXPECTED_NET_EDGE_LOW")
    if trend_alignment < float(limits.min_trend_alignment_pct):
        _append_unique(reason_codes, "MTF_TREND_ALIGNMENT_LOW")
    if feature_sep < float(limits.min_feature_separation_score):
        _append_unique(reason_codes, "MTF_FEATURE_SEPARATION_LOW")
    if not candidate.approvable:
        _append_unique(reason_codes, "DIAGNOSTIC_INTERVAL_NOT_APPROVABLE")

    if action_pct < limits.min_action_pct * 1.25:
        _append_unique(warnings, "ACTION_RATE_NEAR_FLOOR")
    if hold_pct > 90.0:
        _append_unique(warnings, "HOLD_DOMINANCE_ELEVATED")

    ok = not reason_codes
    score = (
        min_expected_edge
        + forward_gap * 0.25
        + (100.0 - abs(action_pct - limits.target_action_pct)) * 0.10
        + entropy * 10.0
        + feature_sep * 50.0
        - max(side_pct - 55.0, 0.0) * 0.40
        - len(reason_codes) * 15.0
    )
    return {
        "contract_version": MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
        "report_type": "multitimeframe_alpha_candidate_gate",
        "decision": "PASS" if ok else "BLOCK",
        "ok": bool(ok),
        "approved_for_training_candidate": bool(ok and candidate.approvable),
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_allowed": False,
        "candidate": candidate.to_dict(),
        "source": source,
        "sample_count": sample_count,
        "clean_samples": sample_count,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "score": round(float(score), 6),
        "metrics": {
            "target_distribution": dist,
            "target_action_pct": action_pct,
            "target_hold_pct": hold_pct,
            "target_action_side_pct": side_pct,
            "target_directional_entropy": entropy,
            "forward_return_bps": {
                "buy": _summary(list(buy_returns)),
                "sell": _summary(list(sell_returns)),
                "hold_abs": _summary(list(hold_abs_returns)),
            },
            "buy_expected_edge_bps": round(float(buy_mean - candidate.effective_min_profit_bps), 6),
            "sell_expected_edge_bps": round(float(sell_mean - candidate.effective_min_profit_bps), 6),
            "min_expected_net_edge_bps": round(float(min_expected_edge), 6),
            "forward_return_gap_bps": round(float(forward_gap), 6),
            "trend_alignment_pct": trend_alignment,
            "feature_separation_score": round(float(feature_sep), 8),
            "effective_min_profit_bps": round(float(candidate.effective_min_profit_bps), 6),
            "interval": candidate.interval,
        },
        "limits": limits.to_dict(),
    }


def _select_best(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return dict(max(candidates, key=lambda item: _safe_float(item.get("score"), -999999.0)))


def build_multitimeframe_alpha_discovery(
    frames_by_interval: Mapping[str, pd.DataFrame],
    *,
    candidates: Sequence[MultiTimeframeAlphaCandidate] | None = None,
    limits: MultiTimeframeAlphaGateLimits | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    limits = limits or MultiTimeframeAlphaGateLimits()
    candidates = list(candidates or default_multitimeframe_alpha_candidates())
    evaluated: list[dict[str, Any]] = []
    available = {str(key): value for key, value in frames_by_interval.items() if isinstance(value, pd.DataFrame)}
    for candidate in candidates:
        frame = available.get(candidate.interval)
        if frame is None:
            evaluated.append({
                "contract_version": MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
                "report_type": "multitimeframe_alpha_candidate_gate",
                "decision": "BLOCK",
                "ok": False,
                "approved_for_training_candidate": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "live_real_allowed": False,
                "candidate": candidate.to_dict(),
                "source": source,
                "sample_count": 0,
                "reason_codes": ["MTF_INTERVAL_DATA_MISSING"],
                "warnings": [],
                "score": -999.0,
                "metrics": {"interval": candidate.interval},
                "limits": limits.to_dict(),
            })
            continue
        evaluated.append(analyze_multitimeframe_alpha_candidate(frame, candidate, limits=limits, source=source))

    pass_candidates = [item for item in evaluated if bool(item.get("approved_for_training_candidate"))]
    selected = _select_best(pass_candidates) or _select_best(evaluated)
    approved = bool(selected and selected.get("approved_for_training_candidate"))
    reason_codes: list[str] = []
    if not approved:
        _append_unique(reason_codes, "NO_MULTITIMEFRAME_ALPHA_CANDIDATE_PASSED")
    if selected:
        for code in selected.get("reason_codes") or []:
            _append_unique(reason_codes, str(code))
    return {
        "contract_version": MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
        "phase": MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION,
        "report_type": "multitimeframe_alpha_discovery_research_reset",
        "decision": "PASS" if approved else "BLOCK",
        "ok": approved,
        "source": source,
        "intervals": sorted(available.keys()),
        "candidate_count": len(evaluated),
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "post_requests_allowed": False,
        "observation_only": True,
        "get_only_public_market_data": True,
        "selected_candidate": selected,
        "selected_policy": (selected or {}).get("candidate") if selected else None,
        "reason_codes": reason_codes,
        "recommendation": (
            "A multi-timeframe alpha candidate passed the research gate. Use it only for controlled offline retrain research; paper/live remain blocked."
            if approved
            else "No multi-timeframe alpha candidate passed. Do not retrain/promote; expand feature families or change research assumptions."
        ),
        "candidates": evaluated,
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
    }


__all__ = [
    "MULTITIMEFRAME_ALPHA_DISCOVERY_CONTRACT_VERSION",
    "MultiTimeframeAlphaCandidate",
    "MultiTimeframeAlphaGateLimits",
    "default_multitimeframe_alpha_candidates",
    "analyze_multitimeframe_alpha_candidate",
    "build_multitimeframe_alpha_discovery",
]
