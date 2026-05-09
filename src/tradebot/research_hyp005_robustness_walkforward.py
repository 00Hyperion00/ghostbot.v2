from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

from tradebot.research_hyp005_liquidity_sweep_reversal_exploration import (
    BRANCH_NAME,
    DEFAULT_STRATEGIES,
    HYPOTHESIS_ID,
    LiquiditySweepStrategySpec,
    load_json,
    normalize_market_frame,
    safe_float,
    safe_int,
    strategy_edges,
    write_json,
)

HYP005_ROBUSTNESS_CONTRACT_VERSION = "4B.4.3.6.6.25T"
REPORT_PREFIX = "4B436625T_hyp005_robustness_walkforward_confirmation"


@dataclass(frozen=True)
class Hyp005RobustnessLimits:
    min_signal_count: int = 25
    min_mean_net_edge_bps: float = 50.0
    min_median_net_edge_bps: float = 30.0
    min_profit_factor: float = 1.50
    min_win_rate_pct: float = 50.0
    min_oos_mean_net_edge_bps: float = 25.0
    min_walk_forward_positive_rate_pct: float = 60.0
    max_top_win_dependency_pct: float = 45.0
    max_dominant_symbol_pct: float = 70.0
    max_wick_dependency_pct: float = 85.0
    min_symbols_traded: int = 2
    min_recent_30d_signal_count: int = 6
    min_recent_30d_mean_edge_bps: float = 0.0
    min_recent_60d_mean_edge_bps: float = 15.0
    max_recent_decay_bps: float = 120.0
    near_floor_signal_count: int = 40
    small_sample_penalty_bps: float = 18.0
    round_trip_cost_bps: float = 16.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def validate_hyp005_25s_report(report: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    if not report:
        return False, ["HYP005_EXPLORATION_REPORT_MISSING"]
    if str(report.get("hypothesis_id") or "") != HYPOTHESIS_ID:
        return False, ["HYP005_EXPLORATION_HYPOTHESIS_MISMATCH"]
    if str(report.get("decision") or "") != "HYP005_EXPLORATION_PASS":
        return False, ["HYP005_EXPLORATION_NOT_PASS"]
    selected = report.get("selected_candidate")
    if not isinstance(selected, Mapping):
        return False, ["HYP005_SELECTED_CANDIDATE_MISSING"]
    if str(selected.get("decision") or "") != "PASS":
        return False, ["HYP005_SELECTED_CANDIDATE_NOT_PASS"]
    if bool(report.get("approved_for_training_candidate")) or bool(report.get("approved_for_paper_candidate")) or bool(report.get("approved_for_live_real")):
        return False, ["HYP005_EXPLORATION_APPROVAL_GUARDRAIL_VIOLATION"]
    return True, []


def selected_spec_from_25s(report: Mapping[str, Any]) -> LiquiditySweepStrategySpec | None:
    selected = report.get("selected_candidate")
    if not isinstance(selected, Mapping):
        return None
    spec_payload = selected.get("spec")
    if isinstance(spec_payload, Mapping):
        try:
            return LiquiditySweepStrategySpec(
                name=str(spec_payload.get("name")),
                lookback_bars=safe_int(spec_payload.get("lookback_bars"), 24),
                hold_bars=safe_int(spec_payload.get("hold_bars"), 6),
                min_sweep_bps=safe_float(spec_payload.get("min_sweep_bps"), 18.0),
                min_wick_pct=safe_float(spec_payload.get("min_wick_pct"), 42.0),
                compression_window=safe_int(spec_payload.get("compression_window"), 12),
                compression_baseline_bars=safe_int(spec_payload.get("compression_baseline_bars"), 48),
                max_compression_ratio=safe_float(spec_payload.get("max_compression_ratio"), 1.05),
                diagnostic_only=bool(spec_payload.get("diagnostic_only", False)),
            )
        except Exception:
            return None
    family = str(selected.get("strategy_family") or "")
    for spec in DEFAULT_STRATEGIES:
        if spec.name == family:
            return spec
    return None


def _empty_metrics() -> dict[str, Any]:
    return {
        "signal_count": 0,
        "mean_net_edge_bps": 0.0,
        "median_net_edge_bps": 0.0,
        "profit_factor": 0.0,
        "win_rate_pct": 0.0,
        "oos_mean_net_edge_bps": 0.0,
        "walk_forward_positive_rate_pct": 0.0,
        "top_win_dependency_pct": 100.0,
        "dominant_symbol_pct": 100.0,
        "wick_dependency_pct": 100.0,
        "symbols_traded": 0,
        "recent_30d_signal_count": 0,
        "recent_30d_mean_edge_bps": 0.0,
        "recent_60d_mean_edge_bps": 0.0,
        "recent_90d_mean_edge_bps": 0.0,
        "recent_edge_decay_bps": 0.0,
        "small_sample_penalty_bps": 0.0,
        "penalized_mean_net_edge_bps": 0.0,
    }


def _profit_factor(values: pd.Series) -> float:
    positives = values[values > 0]
    negatives = values[values < 0]
    gross_profit = float(positives.sum())
    gross_loss = abs(float(negatives.sum()))
    if gross_loss <= 1e-12:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def split_dataframe(df: pd.DataFrame, parts: int) -> list[pd.DataFrame]:
    if df.empty:
        return []
    indexes = np.array_split(np.arange(len(df)), max(1, int(parts)))
    return [df.iloc[idx].copy() for idx in indexes if len(idx) > 0]


def _recent_window(edges: pd.DataFrame, days: int) -> pd.DataFrame:
    if edges.empty or "open_time" not in edges.columns:
        return edges.iloc[0:0].copy()
    max_time = safe_float(pd.to_numeric(edges["open_time"], errors="coerce").max(), 0.0)
    if max_time <= 0:
        return edges.iloc[0:0].copy()
    start = max_time - days * 24 * 60 * 60 * 1000
    return edges[pd.to_numeric(edges["open_time"], errors="coerce") >= start].copy()


def summarize_robust_edges(edges: pd.DataFrame, *, limits: Hyp005RobustnessLimits) -> dict[str, Any]:
    if edges.empty or "net_edge_bps" not in edges.columns:
        return _empty_metrics()
    ordered = edges.sort_values("open_time").reset_index(drop=True)
    values = pd.to_numeric(ordered["net_edge_bps"], errors="coerce").dropna()
    if values.empty:
        return _empty_metrics()
    signal_count = int(len(values))
    profit_factor = _profit_factor(values)
    positives = values[values > 0].sort_values(ascending=False)
    gross_profit = float(positives.sum())
    top_win_dependency_pct = float(positives.head(3).sum() / gross_profit * 100.0) if gross_profit > 1e-12 else 100.0
    symbol_counts = ordered["symbol"].astype(str).value_counts() if "symbol" in ordered.columns else pd.Series(dtype=float)
    dominant_symbol_pct = float(symbol_counts.iloc[0] / len(ordered) * 100.0) if not symbol_counts.empty else 100.0
    symbols_traded = int(symbol_counts.shape[0]) if not symbol_counts.empty else 0
    wick = pd.to_numeric(ordered.get("wick_pct", pd.Series(dtype=float)), errors="coerce").dropna()
    wick_dependency_pct = float((wick >= limits.max_wick_dependency_pct).mean() * 100.0) if not wick.empty else 100.0
    oos_start = int(len(ordered) * 0.70)
    oos = ordered.iloc[oos_start:] if oos_start < len(ordered) else ordered.iloc[0:0]
    oos_values = pd.to_numeric(oos.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").dropna()
    walk_chunks = split_dataframe(ordered, 4)
    positive_chunks = [safe_float(pd.to_numeric(chunk["net_edge_bps"], errors="coerce").mean()) > limits.min_recent_60d_mean_edge_bps for chunk in walk_chunks if not chunk.empty]
    recent_30 = _recent_window(ordered, 30)
    recent_60 = _recent_window(ordered, 60)
    recent_90 = _recent_window(ordered, 90)
    recent_30_values = pd.to_numeric(recent_30.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").dropna()
    recent_60_values = pd.to_numeric(recent_60.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").dropna()
    recent_90_values = pd.to_numeric(recent_90.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").dropna()
    mean_edge = float(values.mean())
    penalty = limits.small_sample_penalty_bps if signal_count < limits.near_floor_signal_count else 0.0
    return {
        "signal_count": signal_count,
        "mean_net_edge_bps": round(mean_edge, 6),
        "median_net_edge_bps": round(float(values.median()), 6),
        "profit_factor": round(float(profit_factor), 6),
        "win_rate_pct": round(float((values > 0).mean() * 100.0), 6),
        "oos_mean_net_edge_bps": round(float(oos_values.mean()) if not oos_values.empty else 0.0, 6),
        "walk_forward_positive_rate_pct": round(float(sum(positive_chunks) / len(positive_chunks) * 100.0) if positive_chunks else 0.0, 6),
        "top_win_dependency_pct": round(top_win_dependency_pct, 6),
        "dominant_symbol_pct": round(dominant_symbol_pct, 6),
        "wick_dependency_pct": round(wick_dependency_pct, 6),
        "symbols_traded": symbols_traded,
        "recent_30d_signal_count": int(len(recent_30_values)),
        "recent_30d_mean_edge_bps": round(float(recent_30_values.mean()) if not recent_30_values.empty else 0.0, 6),
        "recent_60d_mean_edge_bps": round(float(recent_60_values.mean()) if not recent_60_values.empty else 0.0, 6),
        "recent_90d_mean_edge_bps": round(float(recent_90_values.mean()) if not recent_90_values.empty else 0.0, 6),
        "recent_edge_decay_bps": round(float((recent_90_values.mean() if not recent_90_values.empty else 0.0) - (recent_30_values.mean() if not recent_30_values.empty else 0.0)), 6),
        "small_sample_penalty_bps": round(float(penalty), 6),
        "penalized_mean_net_edge_bps": round(float(mean_edge - penalty), 6),
    }


def evaluate_robustness(metrics: Mapping[str, Any], *, limits: Hyp005RobustnessLimits, spec: LiquiditySweepStrategySpec | None) -> tuple[str, list[str], list[str], float]:
    reasons: list[str] = []
    warnings: list[str] = []
    if spec is None:
        reasons.append("HYP005_SELECTED_SPEC_MISSING")
    elif spec.diagnostic_only:
        reasons.append("HYP005_DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if safe_int(metrics.get("signal_count")) < limits.min_signal_count:
        reasons.append("ROBUST_SIGNAL_COUNT_LOW")
    if safe_float(metrics.get("penalized_mean_net_edge_bps")) < limits.min_mean_net_edge_bps:
        reasons.append("ROBUST_MEAN_EDGE_LOW_AFTER_SMALL_SAMPLE_PENALTY")
    if safe_float(metrics.get("mean_net_edge_bps")) < limits.min_mean_net_edge_bps:
        reasons.append("ROBUST_MEAN_EDGE_LOW")
    if safe_float(metrics.get("median_net_edge_bps")) < limits.min_median_net_edge_bps:
        reasons.append("ROBUST_MEDIAN_EDGE_LOW")
    if safe_float(metrics.get("profit_factor")) < limits.min_profit_factor:
        reasons.append("ROBUST_PROFIT_FACTOR_LOW")
    if safe_float(metrics.get("win_rate_pct")) < limits.min_win_rate_pct:
        reasons.append("ROBUST_WIN_RATE_LOW")
    if safe_float(metrics.get("oos_mean_net_edge_bps")) < limits.min_oos_mean_net_edge_bps:
        reasons.append("ROBUST_OOS_EDGE_LOW")
    if safe_float(metrics.get("walk_forward_positive_rate_pct")) < limits.min_walk_forward_positive_rate_pct:
        reasons.append("ROBUST_WALK_FORWARD_STABILITY_LOW")
    if safe_float(metrics.get("top_win_dependency_pct"), 100.0) > limits.max_top_win_dependency_pct:
        reasons.append("ROBUST_TOP_WIN_DEPENDENCY_HIGH")
    if safe_float(metrics.get("dominant_symbol_pct"), 100.0) > limits.max_dominant_symbol_pct:
        reasons.append("ROBUST_DOMINANT_SYMBOL_DEPENDENCY_HIGH")
    if safe_float(metrics.get("wick_dependency_pct"), 100.0) > limits.max_wick_dependency_pct:
        reasons.append("ROBUST_WICK_DEPENDENCY_HIGH")
    if safe_int(metrics.get("symbols_traded")) < limits.min_symbols_traded:
        reasons.append("ROBUST_SYMBOL_DIVERSITY_LOW")
    if safe_int(metrics.get("recent_30d_signal_count")) < limits.min_recent_30d_signal_count:
        reasons.append("ROBUST_RECENT_30D_SIGNAL_COUNT_LOW")
    if safe_float(metrics.get("recent_30d_mean_edge_bps")) < limits.min_recent_30d_mean_edge_bps:
        reasons.append("ROBUST_RECENT_30D_EDGE_LOW")
    if safe_float(metrics.get("recent_60d_mean_edge_bps")) < limits.min_recent_60d_mean_edge_bps:
        reasons.append("ROBUST_RECENT_60D_EDGE_LOW")
    if safe_float(metrics.get("recent_edge_decay_bps")) > limits.max_recent_decay_bps:
        reasons.append("ROBUST_RECENT_EDGE_DECAY_HIGH")
    if safe_int(metrics.get("signal_count")) < limits.near_floor_signal_count:
        warnings.append("ROBUST_SMALL_SAMPLE_PENALTY_APPLIED")
    score = (
        safe_float(metrics.get("penalized_mean_net_edge_bps"))
        + safe_float(metrics.get("median_net_edge_bps")) * 0.8
        + safe_float(metrics.get("oos_mean_net_edge_bps")) * 0.55
        + safe_float(metrics.get("profit_factor")) * 10.0
        + safe_float(metrics.get("walk_forward_positive_rate_pct")) * 0.18
        - safe_float(metrics.get("top_win_dependency_pct"), 100.0) * 0.25
        - safe_float(metrics.get("dominant_symbol_pct"), 100.0) * 0.08
    )
    return ("PASS" if not reasons else "BLOCK", reasons, warnings, round(float(score), 6))


def build_hyp005_robustness_walkforward_report(
    market_df: pd.DataFrame,
    *,
    exploration_report: Mapping[str, Any] | None = None,
    source: str = "unknown",
    limits: Hyp005RobustnessLimits | None = None,
) -> dict[str, Any]:
    limits = limits or Hyp005RobustnessLimits()
    selection_ok, selection_reasons = validate_hyp005_25s_report(exploration_report)
    spec = selected_spec_from_25s(exploration_report or {}) if selection_ok else None
    normalized = normalize_market_frame(market_df)
    edges = strategy_edges(normalized, spec, limits.round_trip_cost_bps) if spec is not None else pd.DataFrame()
    metrics = summarize_robust_edges(edges, limits=limits)
    candidate_decision, candidate_reasons, candidate_warnings, score = evaluate_robustness(metrics, limits=limits, spec=spec)
    reason_codes: list[str] = []
    if not selection_ok:
        reason_codes.extend(selection_reasons)
    if candidate_decision != "PASS":
        reason_codes.extend(candidate_reasons)
    decision = "HYP005_ROBUSTNESS_PASS" if selection_ok and candidate_decision == "PASS" else "HYP005_ROBUSTNESS_BLOCK"
    approved = decision == "HYP005_ROBUSTNESS_PASS"
    selected_candidate = {
        "strategy_family": spec.name if spec else None,
        "spec": asdict(spec) if spec else None,
        "decision": candidate_decision,
        "ok": candidate_decision == "PASS",
        "score": score,
        "metrics": metrics,
        "reason_codes": candidate_reasons,
        "warnings": candidate_warnings,
        "approved_for_research_candidate": approved,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
    }
    report = {
        "contract_version": HYP005_ROBUSTNESS_CONTRACT_VERSION,
        "phase": "25T",
        "report_type": "hyp005_robustness_walkforward_confirmation_gate",
        "generated_at": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "source": source,
        "symbols": sorted(normalized["symbol"].astype(str).unique().tolist()),
        "decision": decision,
        "ok": approved,
        "selected_candidate": selected_candidate,
        "edge_sample_count": int(len(edges)),
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(candidate_warnings)),
        "recommendation": (
            "HYP-005 liquidity sweep reversal candidate passed robustness/walk-forward as a research-only candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated no-order shadow planning/spec gate first."
            if approved
            else "HYP-005 liquidity sweep reversal candidate failed robustness/walk-forward confirmation. Do not train, reload, paper trade, or enable live trading; refine or close this candidate."
        ),
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "public_market_data_get_only": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "training_allowed": False,
            "paper_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
        "approved_for_research_candidate": approved,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }
    return report


def report_to_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_candidate") or {}
    metrics = selected.get("metrics", {}) if isinstance(selected, Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25T HYP-005 Robustness / Walk-Forward Confirmation Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_strategy_family: `{selected.get('strategy_family') if isinstance(selected, Mapping) else None}`",
        f"- signal_count: `{metrics.get('signal_count')}`",
        f"- mean_net_edge_bps: `{metrics.get('mean_net_edge_bps')}`",
        f"- penalized_mean_net_edge_bps: `{metrics.get('penalized_mean_net_edge_bps')}`",
        f"- median_net_edge_bps: `{metrics.get('median_net_edge_bps')}`",
        f"- profit_factor: `{metrics.get('profit_factor')}`",
        f"- win_rate_pct: `{metrics.get('win_rate_pct')}`",
        f"- oos_mean_net_edge_bps: `{metrics.get('oos_mean_net_edge_bps')}`",
        f"- walk_forward_positive_rate_pct: `{metrics.get('walk_forward_positive_rate_pct')}`",
        f"- top_win_dependency_pct: `{metrics.get('top_win_dependency_pct')}`",
        f"- dominant_symbol_pct: `{metrics.get('dominant_symbol_pct')}`",
        f"- wick_dependency_pct: `{metrics.get('wick_dependency_pct')}`",
        f"- recent_30d_signal_count: `{metrics.get('recent_30d_signal_count')}`",
        f"- recent_30d_mean_edge_bps: `{metrics.get('recent_30d_mean_edge_bps')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
        "- observation_only: `True`",
        "- public_market_data_get_only: `True`",
        "- post_requests_allowed: `False`",
        "- config_mutation_performed: `False`",
        "- order_actions_performed: `False`",
        "- reload_performed: `False`",
        "- live_real_allowed: `False`",
        "- Training remains blocked.",
        "- Paper/live remain blocked.",
    ]
    return "\n".join(lines) + "\n"
