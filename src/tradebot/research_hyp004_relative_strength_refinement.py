from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

HYP004_REFINEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25P"
REPORT_PREFIX = "4B436625P_hyp004_relative_strength_refinement"
HYPOTHESIS_ID = "HYP-004"
BRANCH_NAME = "cross_symbol_relative_strength_rotation"

BUY = "BUY"
HOLD = "HOLD"


@dataclass(frozen=True)
class RelativeStrengthRefinementSpec:
    name: str
    base_family: str = "laggard_reversion"
    lookback_bars: int = 24
    hold_bars: int = 6
    min_spread_bps: float = 30.0
    min_laggard_underperformance_bps: float = 10.0
    max_abs_laggard_return_bps: float = 750.0
    cooldown_bars: int = 1
    allow_repeat_symbol: bool = True
    diagnostic_only: bool = False


@dataclass(frozen=True)
class RelativeStrengthRefinementLimits:
    min_signal_count: int = 80
    min_mean_net_edge_bps: float = 25.0
    min_median_net_edge_bps: float = 12.0
    min_profit_factor: float = 1.35
    min_win_rate_pct: float = 49.0
    min_oos_mean_net_edge_bps: float = 10.0
    min_walk_forward_positive_rate_pct: float = 65.0
    max_dominant_symbol_pct: float = 65.0
    max_top_win_dependency_pct: float = 30.0
    min_symbols_traded: int = 2
    round_trip_cost_bps: float = 16.0


DEFAULT_REFINEMENT_SPECS: tuple[RelativeStrengthRefinementSpec, ...] = (
    RelativeStrengthRefinementSpec(
        name="laggard_reversion_guarded_lb24_h6_spread30",
        lookback_bars=24,
        hold_bars=6,
        min_spread_bps=30.0,
        min_laggard_underperformance_bps=15.0,
        cooldown_bars=1,
    ),
    RelativeStrengthRefinementSpec(
        name="laggard_reversion_guarded_lb36_h8_spread40",
        lookback_bars=36,
        hold_bars=8,
        min_spread_bps=40.0,
        min_laggard_underperformance_bps=20.0,
        cooldown_bars=1,
    ),
    RelativeStrengthRefinementSpec(
        name="laggard_reversion_guarded_lb18_h4_spread35",
        lookback_bars=18,
        hold_bars=4,
        min_spread_bps=35.0,
        min_laggard_underperformance_bps=15.0,
        cooldown_bars=2,
    ),
    RelativeStrengthRefinementSpec(
        name="laggard_reversion_symbol_cooldown_lb24_h8_spread45",
        lookback_bars=24,
        hold_bars=8,
        min_spread_bps=45.0,
        min_laggard_underperformance_bps=20.0,
        cooldown_bars=3,
        allow_repeat_symbol=False,
    ),
    RelativeStrengthRefinementSpec(
        name="laggard_reversion_diagnostic_loose_probe",
        lookback_bars=12,
        hold_bars=3,
        min_spread_bps=20.0,
        min_laggard_underperformance_bps=5.0,
        cooldown_bars=0,
        diagnostic_only=True,
    ),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def validate_hyp004_25o_report(report: Mapping[str, Any] | None) -> tuple[bool, list[str], str]:
    if not report:
        return False, ["HYP004_25O_REPORT_MISSING"], ""
    hypothesis_id = str(report.get("hypothesis_id") or report.get("selected_next_hypothesis_id") or "")
    decision = str(report.get("decision") or "")
    selected = report.get("selected_candidate") if isinstance(report.get("selected_candidate"), Mapping) else {}
    selected_family = str(selected.get("strategy_family") or report.get("selected_strategy_family") or "")
    reasons = []
    if hypothesis_id != HYPOTHESIS_ID:
        reasons.append("HYP004_25O_HYPOTHESIS_MISMATCH")
    if decision not in {"HYP004_EXPLORATION_BLOCK", "HYP004_EXPLORATION_PASS"}:
        reasons.append("HYP004_25O_DECISION_INVALID")
    if not selected_family:
        reasons.append("HYP004_25O_SELECTED_FAMILY_MISSING")
    return not reasons, reasons, selected_family


def normalize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "open_time", "close"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"market frame missing required columns: {missing}")
    out = df.copy()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["open_time"] = pd.to_numeric(out["open_time"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["symbol", "open_time", "close"])
    out = out.sort_values(["open_time", "symbol"]).reset_index(drop=True)
    if out.empty:
        raise ValueError("market frame has no usable rows")
    return out


def build_price_matrix(df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_market_frame(df)
    matrix = normalized.pivot_table(index="open_time", columns="symbol", values="close", aggfunc="last")
    matrix = matrix.sort_index().ffill().dropna(axis=1, how="all")
    matrix = matrix.dropna(how="any")
    if matrix.shape[1] < 2:
        raise ValueError("at least two symbols are required for HYP-004 refinement")
    return matrix


def _forward_return_bps(prices: pd.DataFrame, hold_bars: int) -> pd.DataFrame:
    return ((prices.shift(-hold_bars) / prices) - 1.0) * 10_000.0


def _edge_row(ts: Any, symbol: str, edge_bps: float, spread_bps: float, spec: RelativeStrengthRefinementSpec, laggard_return_bps: float) -> dict[str, Any]:
    return {
        "open_time": int(ts),
        "symbol": str(symbol),
        "side": BUY,
        "strategy_family": spec.base_family,
        "refinement_name": spec.name,
        "lookback_bars": spec.lookback_bars,
        "hold_bars": spec.hold_bars,
        "spread_bps": round(float(spread_bps), 6),
        "laggard_return_bps": round(float(laggard_return_bps), 6),
        "net_edge_bps": round(float(edge_bps), 6),
    }


def _refined_laggard_edges(prices: pd.DataFrame, spec: RelativeStrengthRefinementSpec, cost_bps: float) -> pd.DataFrame:
    returns = prices.pct_change(spec.lookback_bars) * 10_000.0
    fwd = _forward_return_bps(prices, spec.hold_bars)
    rows: list[dict[str, Any]] = []
    cooldown: dict[str, int] = {symbol: -10_000 for symbol in prices.columns}
    for idx, (ts, row) in enumerate(returns.iterrows()):
        if row.isna().any() or ts not in fwd.index:
            continue
        future = fwd.loc[ts]
        if future.isna().any():
            continue
        ranked = row.sort_values(ascending=False)
        leader = str(ranked.index[0])
        laggard = str(ranked.index[-1])
        spread_bps = float(ranked.loc[leader] - ranked.loc[laggard])
        laggard_return = float(ranked.loc[laggard])
        if spread_bps < spec.min_spread_bps:
            continue
        if abs(laggard_return) > spec.max_abs_laggard_return_bps:
            continue
        if (float(row.mean()) - laggard_return) < spec.min_laggard_underperformance_bps:
            continue
        if not spec.allow_repeat_symbol and idx - cooldown.get(laggard, -10_000) <= spec.cooldown_bars:
            continue
        edge = float(future[laggard] - cost_bps)
        rows.append(_edge_row(ts, laggard, edge, spread_bps, spec, laggard_return))
        cooldown[laggard] = idx
    return pd.DataFrame(rows)


def split_dataframe(df: pd.DataFrame, parts: int) -> list[pd.DataFrame]:
    if parts <= 0:
        raise ValueError("parts must be positive")
    if df.empty:
        return []
    indices = np.array_split(np.arange(len(df)), min(parts, len(df)))
    return [df.iloc[idx].copy() for idx in indices if len(idx) > 0]


def summarize_edges(edges: pd.DataFrame, *, limits: RelativeStrengthRefinementLimits) -> dict[str, Any]:
    if edges.empty:
        return {
            "signal_count": 0,
            "mean_net_edge_bps": 0.0,
            "median_net_edge_bps": 0.0,
            "profit_factor": 0.0,
            "win_rate_pct": 0.0,
            "oos_mean_net_edge_bps": 0.0,
            "walk_forward_positive_rate_pct": 0.0,
            "dominant_symbol_pct": 0.0,
            "top_win_dependency_pct": 100.0,
            "symbols_traded": 0,
        }
    ordered = edges.sort_values("open_time").reset_index(drop=True)
    values = pd.to_numeric(ordered["net_edge_bps"], errors="coerce").dropna()
    if values.empty:
        return summarize_edges(pd.DataFrame(), limits=limits)
    positives = values[values > 0]
    negatives = values[values < 0]
    gross_profit = float(positives.sum())
    gross_loss = abs(float(negatives.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else (999.0 if gross_profit > 0 else 0.0)
    oos_start = int(len(ordered) * 0.70)
    oos = ordered.iloc[oos_start:] if oos_start < len(ordered) else ordered.iloc[0:0]
    wf = split_dataframe(ordered, 5)
    wf_positive = [safe_float(chunk["net_edge_bps"].mean()) > limits.min_oos_mean_net_edge_bps for chunk in wf if not chunk.empty]
    symbol_counts = ordered["symbol"].astype(str).value_counts()
    dominant_symbol_pct = float(symbol_counts.iloc[0] / len(ordered) * 100.0) if not symbol_counts.empty else 0.0
    top_positive = positives.sort_values(ascending=False)
    top_win_dependency_pct = float(top_positive.head(5).sum() / gross_profit * 100.0) if gross_profit > 1e-12 else 100.0
    return {
        "signal_count": int(len(values)),
        "mean_net_edge_bps": round(float(values.mean()), 6),
        "median_net_edge_bps": round(float(values.median()), 6),
        "profit_factor": round(float(profit_factor), 6),
        "win_rate_pct": round(float((values > 0).mean() * 100.0), 6),
        "oos_mean_net_edge_bps": round(float(pd.to_numeric(oos.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").mean()) if not oos.empty else 0.0, 6),
        "walk_forward_positive_rate_pct": round(float(sum(wf_positive) / len(wf_positive) * 100.0) if wf_positive else 0.0, 6),
        "dominant_symbol_pct": round(float(dominant_symbol_pct), 6),
        "top_win_dependency_pct": round(float(top_win_dependency_pct), 6),
        "symbols_traded": int(symbol_counts.shape[0]),
    }


def evaluate_refined_candidate(
    edges: pd.DataFrame,
    *,
    spec: RelativeStrengthRefinementSpec,
    limits: RelativeStrengthRefinementLimits,
    symbol_count: int,
) -> dict[str, Any]:
    metrics = summarize_edges(edges, limits=limits)
    reason_codes: list[str] = []
    warnings: list[str] = []
    if spec.diagnostic_only:
        reason_codes.append("DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE")
    if metrics["signal_count"] < limits.min_signal_count:
        reason_codes.append("HYP004_REFINED_SIGNAL_COUNT_LOW")
    if metrics["mean_net_edge_bps"] < limits.min_mean_net_edge_bps:
        reason_codes.append("HYP004_REFINED_MEAN_EDGE_LOW")
    if metrics["median_net_edge_bps"] < limits.min_median_net_edge_bps:
        reason_codes.append("HYP004_REFINED_MEDIAN_EDGE_LOW")
    if metrics["profit_factor"] < limits.min_profit_factor:
        reason_codes.append("HYP004_REFINED_PROFIT_FACTOR_LOW")
    if metrics["win_rate_pct"] < limits.min_win_rate_pct:
        reason_codes.append("HYP004_REFINED_WIN_RATE_LOW")
    if metrics["oos_mean_net_edge_bps"] < limits.min_oos_mean_net_edge_bps:
        reason_codes.append("HYP004_REFINED_OOS_EDGE_LOW")
    if metrics["walk_forward_positive_rate_pct"] < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("HYP004_REFINED_WALK_FORWARD_STABILITY_LOW")
    if metrics["dominant_symbol_pct"] > limits.max_dominant_symbol_pct:
        reason_codes.append("HYP004_REFINED_DOMINANT_SYMBOL_DEPENDENCY_HIGH")
    if metrics["top_win_dependency_pct"] > limits.max_top_win_dependency_pct:
        reason_codes.append("HYP004_REFINED_TOP_WIN_DEPENDENCY_HIGH")
    if metrics["symbols_traded"] < min(limits.min_symbols_traded, symbol_count):
        reason_codes.append("HYP004_REFINED_TRADED_SYMBOL_COUNT_LOW")
    decision = "PASS" if not reason_codes else "BLOCK"
    score = (
        metrics["mean_net_edge_bps"] * 1.0
        + metrics["median_net_edge_bps"] * 1.2
        + metrics["profit_factor"] * 8.0
        + metrics["oos_mean_net_edge_bps"] * 0.75
        + metrics["walk_forward_positive_rate_pct"] * 0.15
        - max(0.0, metrics["dominant_symbol_pct"] - 55.0) * 0.35
        - max(0.0, metrics["top_win_dependency_pct"] - 25.0) * 0.35
    )
    if decision == "BLOCK" and metrics["signal_count"] >= limits.min_signal_count and metrics["mean_net_edge_bps"] > 0 and metrics["median_net_edge_bps"] > 0:
        warnings.append("REFINEMENT_NEAR_MISS_POSITIVE_EDGE")
    return {
        "contract_version": HYP004_REFINEMENT_CONTRACT_VERSION,
        "decision": decision,
        "ok": decision == "PASS",
        "strategy_family": spec.base_family,
        "refinement_name": spec.name,
        "strategy_spec": asdict(spec),
        "metrics": metrics,
        "score": round(float(score), 6),
        "reason_codes": reason_codes,
        "warnings": warnings,
        "approved_for_research_candidate": decision == "PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
    }


def build_hyp004_relative_strength_refinement_report(
    market_df: pd.DataFrame,
    *,
    exploration_report: Mapping[str, Any] | None = None,
    source: str = "unknown",
    specs: Sequence[RelativeStrengthRefinementSpec] = DEFAULT_REFINEMENT_SPECS,
    limits: RelativeStrengthRefinementLimits | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    limits = limits or RelativeStrengthRefinementLimits()
    validation_ok, validation_reasons, selected_family = validate_hyp004_25o_report(exploration_report)
    prices = build_price_matrix(market_df)
    candidates: list[dict[str, Any]] = []
    for spec in specs:
        edges = _refined_laggard_edges(prices, spec, limits.round_trip_cost_bps)
        candidate = evaluate_refined_candidate(edges, spec=spec, limits=limits, symbol_count=prices.shape[1])
        candidate["sample_edges"] = edges.head(10).to_dict(orient="records") if not edges.empty else []
        candidates.append(candidate)
    pass_candidates = [c for c in candidates if c["decision"] == "PASS"]
    pass_candidates.sort(key=lambda c: (safe_float(c.get("score")), safe_float(c.get("metrics", {}).get("profit_factor"))), reverse=True)
    selected = pass_candidates[0] if pass_candidates else max(candidates, key=lambda c: safe_float(c.get("score")), default=None)
    reason_codes: list[str] = []
    if not validation_ok:
        reason_codes.extend(validation_reasons)
    if selected_family and selected_family != "laggard_reversion":
        reason_codes.append("HYP004_SELECTED_FAMILY_NOT_LAGGARD_REVERSION")
    if pass_candidates:
        reason_codes.append("HYP004_REFINED_RESEARCH_CANDIDATE_IDENTIFIED")
    else:
        reason_codes.append("NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED")
        for code in sorted({code for c in candidates for code in c.get("reason_codes", [])}):
            reason_codes.append(code)
    decision = "HYP004_REFINEMENT_PASS" if validation_ok and selected_family == "laggard_reversion" and pass_candidates else "HYP004_REFINEMENT_BLOCK"
    approved_for_research = decision == "HYP004_REFINEMENT_PASS"
    next_candidate_spec = None
    if approved_for_research and isinstance(selected, Mapping):
        next_candidate_spec = {
            "contract_version": HYP004_REFINEMENT_CONTRACT_VERSION,
            "hypothesis_id": HYPOTHESIS_ID,
            "branch_name": BRANCH_NAME,
            "symbol_universe": list(prices.columns),
            "strategy_family": selected.get("strategy_family"),
            "refinement_name": selected.get("refinement_name"),
            "strategy_spec": selected.get("strategy_spec"),
            "source_report_type": "hyp004_relative_strength_refinement",
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "live_real_allowed": False,
        }
    return {
        "contract_version": HYP004_REFINEMENT_CONTRACT_VERSION,
        "phase": "25P",
        "report_type": "hyp004_relative_strength_candidate_refinement_approvable_strategy_gate",
        "generated_at": generated_at or utc_now_iso(),
        "decision": decision,
        "ok": approved_for_research,
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "source": source,
        "symbols": list(prices.columns),
        "bar_count": int(prices.shape[0]),
        "selected_25o_family": selected_family,
        "candidate_count": len(candidates),
        "passed_candidate_count": len(pass_candidates),
        "selected_candidate": selected,
        "candidates": candidates,
        "limits": asdict(limits),
        "next_candidate_spec": next_candidate_spec,
        "reason_codes": sorted(set(reason_codes)),
        "recommendation": (
            "A non-diagnostic HYP-004 refined relative-strength candidate passed. Keep it research-only and move to robustness confirmation; do not train, reload, paper trade, or enable live trading."
            if approved_for_research
            else "No approvable HYP-004 refined relative-strength candidate passed. Do not train, reload, paper trade, or enable live trading; close or return to backlog."
        ),
        "approved_for_research_candidate": approved_for_research,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "guardrails": {
            "observation_only": True,
            "public_market_data_GET_only": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "training_allowed": False,
            "paper_allowed": False,
        },
    }


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def report_to_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_candidate") if isinstance(report.get("selected_candidate"), Mapping) else {}
    metrics = selected.get("metrics", {}) if isinstance(selected.get("metrics"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25P HYP-004 Relative Strength Candidate Refinement / Approvable Strategy Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_25o_family: `{report.get('selected_25o_family')}`",
        f"- symbols: `{', '.join(report.get('symbols', []))}`",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- passed_candidate_count: `{report.get('passed_candidate_count')}`",
        f"- selected_refinement_name: `{selected.get('refinement_name')}`",
        f"- selected_signal_count: `{metrics.get('signal_count')}`",
        f"- selected_mean_net_edge_bps: `{metrics.get('mean_net_edge_bps')}`",
        f"- selected_median_net_edge_bps: `{metrics.get('median_net_edge_bps')}`",
        f"- selected_profit_factor: `{metrics.get('profit_factor')}`",
        f"- selected_oos_mean_net_edge_bps: `{metrics.get('oos_mean_net_edge_bps')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Candidates",
        "",
        "| refinement | decision | score | signals | mean | median | pf | oos | wf+ | dom_sym | top_win | reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for candidate in report.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        m = candidate.get("metrics", {}) if isinstance(candidate.get("metrics"), Mapping) else {}
        lines.append(
            f"| {candidate.get('refinement_name')} | {candidate.get('decision')} | {candidate.get('score')} | {m.get('signal_count')} | "
            f"{m.get('mean_net_edge_bps')} | {m.get('median_net_edge_bps')} | {m.get('profit_factor')} | {m.get('oos_mean_net_edge_bps')} | "
            f"{m.get('walk_forward_positive_rate_pct')} | {m.get('dominant_symbol_pct')} | {m.get('top_win_dependency_pct')} | `{candidate.get('reason_codes')}` |"
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This gate may identify a research-only refined candidate. It never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders.",
    ])
    return "\n".join(lines) + "\n"
