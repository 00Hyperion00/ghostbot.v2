from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

HYP004_EXPLORATION_CONTRACT_VERSION = "4B.4.3.6.6.25O"
REPORT_PREFIX = "4B436625O_hyp004_cross_symbol_relative_strength_exploration"
HYPOTHESIS_ID = "HYP-004"
BRANCH_NAME = "cross_symbol_relative_strength_rotation"

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass(frozen=True)
class CrossSymbolStrategySpec:
    name: str
    lookback_bars: int
    hold_bars: int
    top_n: int = 1
    bottom_n: int = 1
    min_spread_bps: float = 20.0
    diagnostic_only: bool = False


@dataclass(frozen=True)
class CrossSymbolExplorationLimits:
    min_signal_count: int = 30
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.15
    min_win_rate_pct: float = 45.0
    min_oos_mean_net_edge_bps: float = 0.0
    min_walk_forward_positive_rate_pct: float = 55.0
    max_dominant_symbol_pct: float = 70.0
    max_top_win_dependency_pct: float = 35.0
    min_symbols_traded: int = 2
    round_trip_cost_bps: float = 16.0


DEFAULT_STRATEGIES: tuple[CrossSymbolStrategySpec, ...] = (
    CrossSymbolStrategySpec("leader_long_momentum", lookback_bars=24, hold_bars=6, min_spread_bps=30.0),
    CrossSymbolStrategySpec("laggard_reversion", lookback_bars=24, hold_bars=6, min_spread_bps=30.0),
    CrossSymbolStrategySpec("leader_laggard_spread", lookback_bars=24, hold_bars=6, min_spread_bps=40.0),
    CrossSymbolStrategySpec("short_term_rotation_probe", lookback_bars=8, hold_bars=3, min_spread_bps=25.0, diagnostic_only=True),
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


def validate_hyp004_selection(report: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    if not report:
        return False, ["HYP004_SELECTION_REPORT_MISSING"]
    selected_id = str(
        report.get("selected_next_hypothesis_id")
        or report.get("hypothesis_id")
        or report.get("selected_hypothesis_id")
        or ""
    )
    decision = str(report.get("decision") or "")
    if selected_id != HYPOTHESIS_ID:
        return False, ["HYP004_NOT_SELECTED"]
    if decision not in {"NEXT_HYPOTHESIS_SELECTED", "HYP004_SELECTED", "REGISTRY_READY"}:
        return False, ["HYP004_SELECTION_DECISION_INVALID"]
    return True, []


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
        raise ValueError("at least two symbols are required for HYP-004 cross-symbol exploration")
    return matrix


def _forward_return_bps(prices: pd.DataFrame, hold_bars: int) -> pd.DataFrame:
    return ((prices.shift(-hold_bars) / prices) - 1.0) * 10_000.0


def _strategy_edges(prices: pd.DataFrame, spec: CrossSymbolStrategySpec, cost_bps: float) -> pd.DataFrame:
    returns = prices.pct_change(spec.lookback_bars) * 10_000.0
    fwd = _forward_return_bps(prices, spec.hold_bars)
    rows: list[dict[str, Any]] = []
    symbols = list(prices.columns)
    for ts, row in returns.iterrows():
        if row.isna().any() or ts not in fwd.index:
            continue
        future = fwd.loc[ts]
        if future.isna().any():
            continue
        ranked = row.sort_values(ascending=False)
        leader = str(ranked.index[0])
        laggard = str(ranked.index[-1])
        spread_bps = float(ranked.iloc[0] - ranked.iloc[-1])
        if spread_bps < spec.min_spread_bps:
            continue

        if spec.name == "leader_long_momentum":
            symbol = leader
            side = BUY
            edge = float(future[symbol] - cost_bps)
            rows.append(_edge_row(ts, symbol, side, edge, spread_bps, spec, row[symbol]))
        elif spec.name == "laggard_reversion":
            symbol = laggard
            side = BUY
            edge = float(future[symbol] - cost_bps)
            rows.append(_edge_row(ts, symbol, side, edge, spread_bps, spec, row[symbol]))
        elif spec.name == "leader_laggard_spread":
            long_symbol = leader
            short_symbol = laggard
            long_edge = float(future[long_symbol] - cost_bps)
            short_edge = float((-future[short_symbol]) - cost_bps)
            pair_edge = (long_edge + short_edge) / 2.0
            pair_symbol = f"{long_symbol}>{short_symbol}"
            rows.append(_edge_row(ts, pair_symbol, "PAIR_LONG_SHORT", pair_edge, spread_bps, spec, row[long_symbol] - row[short_symbol]))
        elif spec.name == "short_term_rotation_probe":
            # Diagnostic: buy the strongest short-term symbol. It is intentionally not approvable.
            symbol = leader
            edge = float(future[symbol] - cost_bps)
            rows.append(_edge_row(ts, symbol, BUY, edge, spread_bps, spec, row[symbol]))
        else:
            raise ValueError(f"unsupported strategy family: {spec.name}")
    return pd.DataFrame(rows)


def _edge_row(
    ts: Any,
    symbol: str,
    side: str,
    edge_bps: float,
    spread_bps: float,
    spec: CrossSymbolStrategySpec,
    relative_strength_bps: float,
) -> dict[str, Any]:
    return {
        "open_time": int(ts),
        "symbol": symbol,
        "side": side,
        "strategy_family": spec.name,
        "lookback_bars": spec.lookback_bars,
        "hold_bars": spec.hold_bars,
        "spread_bps": round(float(spread_bps), 6),
        "relative_strength_bps": round(float(relative_strength_bps), 6),
        "net_edge_bps": round(float(edge_bps), 6),
    }


def summarize_edges(edges: pd.DataFrame, *, limits: CrossSymbolExplorationLimits) -> dict[str, Any]:
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
    values = pd.to_numeric(edges["net_edge_bps"], errors="coerce").dropna()
    if values.empty:
        return summarize_edges(pd.DataFrame(), limits=limits)
    positives = values[values > 0]
    negatives = values[values < 0]
    gross_profit = float(positives.sum())
    gross_loss = abs(float(negatives.sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else (999.0 if gross_profit > 0 else 0.0)
    ordered = edges.sort_values("open_time")
    oos_start = int(len(ordered) * 0.70)
    oos = ordered.iloc[oos_start:] if oos_start < len(ordered) else ordered.iloc[0:0]
    wf = split_dataframe(ordered, 4)
    wf_positive = [safe_float(chunk["net_edge_bps"].mean()) > limits.min_mean_net_edge_bps for chunk in wf if not chunk.empty]
    symbol_counts = edges["symbol"].astype(str).value_counts()
    dominant_symbol_pct = float(symbol_counts.iloc[0] / len(edges) * 100.0) if not symbol_counts.empty else 0.0
    top_positive = positives.sort_values(ascending=False)
    top_win_dependency_pct = float(top_positive.head(3).sum() / gross_profit * 100.0) if gross_profit > 1e-12 else 100.0
    return {
        "signal_count": int(len(values)),
        "mean_net_edge_bps": round(float(values.mean()), 6),
        "median_net_edge_bps": round(float(values.median()), 6),
        "profit_factor": round(float(profit_factor), 6),
        "win_rate_pct": round(float((values > 0).mean() * 100.0), 6),
        "oos_mean_net_edge_bps": round(float(pd.to_numeric(oos.get("net_edge_bps", pd.Series(dtype=float)), errors="coerce").mean()) if not oos.empty else 0.0, 6),
        "walk_forward_positive_rate_pct": round(float(sum(wf_positive) / len(wf_positive) * 100.0) if wf_positive else 0.0, 6),
        "dominant_symbol_pct": round(dominant_symbol_pct, 6),
        "top_win_dependency_pct": round(top_win_dependency_pct, 6),
        "symbols_traded": int(symbol_counts.shape[0]),
    }


def split_dataframe(df: pd.DataFrame, parts: int) -> list[pd.DataFrame]:
    if parts <= 0:
        raise ValueError("parts must be positive")
    if df.empty:
        return []
    indices = np.array_split(np.arange(len(df)), min(parts, len(df)))
    return [df.iloc[idx].copy() for idx in indices if len(idx) > 0]


def evaluate_candidate(
    edges: pd.DataFrame,
    *,
    spec: CrossSymbolStrategySpec,
    limits: CrossSymbolExplorationLimits,
    symbol_count: int,
) -> dict[str, Any]:
    metrics = summarize_edges(edges, limits=limits)
    reason_codes: list[str] = []
    warnings: list[str] = []
    if spec.diagnostic_only:
        reason_codes.append("DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if metrics["signal_count"] < limits.min_signal_count:
        reason_codes.append("HYP004_SIGNAL_COUNT_LOW")
    if metrics["mean_net_edge_bps"] <= limits.min_mean_net_edge_bps:
        reason_codes.append("HYP004_MEAN_EDGE_LOW")
    if metrics["median_net_edge_bps"] <= limits.min_median_net_edge_bps:
        reason_codes.append("HYP004_MEDIAN_EDGE_LOW")
    if metrics["profit_factor"] < limits.min_profit_factor:
        reason_codes.append("HYP004_PROFIT_FACTOR_LOW")
    if metrics["win_rate_pct"] < limits.min_win_rate_pct:
        reason_codes.append("HYP004_WIN_RATE_LOW")
    if metrics["oos_mean_net_edge_bps"] <= limits.min_oos_mean_net_edge_bps:
        reason_codes.append("HYP004_OOS_EDGE_LOW")
    if metrics["walk_forward_positive_rate_pct"] < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("HYP004_WALK_FORWARD_STABILITY_LOW")
    if metrics["dominant_symbol_pct"] > limits.max_dominant_symbol_pct:
        reason_codes.append("HYP004_DOMINANT_SYMBOL_DEPENDENCY_HIGH")
    if metrics["top_win_dependency_pct"] > limits.max_top_win_dependency_pct:
        reason_codes.append("HYP004_TOP_WIN_DEPENDENCY_HIGH")
    if metrics["symbols_traded"] < min(limits.min_symbols_traded, symbol_count):
        reason_codes.append("HYP004_TRADED_SYMBOL_COUNT_LOW")
    decision = "PASS" if not reason_codes else "BLOCK"
    score = (
        metrics["mean_net_edge_bps"]
        + metrics["median_net_edge_bps"]
        + metrics["profit_factor"] * 5.0
        + metrics["walk_forward_positive_rate_pct"] * 0.1
        - max(0.0, metrics["dominant_symbol_pct"] - 55.0) * 0.2
        - max(0.0, metrics["top_win_dependency_pct"] - 25.0) * 0.2
    )
    return {
        "contract_version": HYP004_EXPLORATION_CONTRACT_VERSION,
        "decision": decision,
        "ok": decision == "PASS",
        "strategy_family": spec.name,
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


def build_hyp004_cross_symbol_relative_strength_exploration_report(
    market_df: pd.DataFrame,
    *,
    selection_report: Mapping[str, Any] | None = None,
    source: str = "unknown",
    strategies: Sequence[CrossSymbolStrategySpec] = DEFAULT_STRATEGIES,
    limits: CrossSymbolExplorationLimits | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    limits = limits or CrossSymbolExplorationLimits()
    selection_ok, selection_reasons = validate_hyp004_selection(selection_report)
    prices = build_price_matrix(market_df)
    candidates: list[dict[str, Any]] = []
    for spec in strategies:
        edges = _strategy_edges(prices, spec, limits.round_trip_cost_bps)
        candidate = evaluate_candidate(edges, spec=spec, limits=limits, symbol_count=prices.shape[1])
        candidate["sample_edges"] = edges.head(10).to_dict(orient="records") if not edges.empty else []
        candidates.append(candidate)
    pass_candidates = [c for c in candidates if c["decision"] == "PASS"]
    pass_candidates.sort(key=lambda c: (safe_float(c.get("score")), safe_float(c.get("metrics", {}).get("profit_factor"))), reverse=True)
    selected = pass_candidates[0] if pass_candidates else max(candidates, key=lambda c: safe_float(c.get("score")), default=None)
    reason_codes: list[str] = []
    if not selection_ok:
        reason_codes.extend(selection_reasons)
    if pass_candidates:
        reason_codes.append("HYP004_RESEARCH_CANDIDATE_IDENTIFIED")
    else:
        reason_codes.append("NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED")
        for code in sorted({code for c in candidates for code in c.get("reason_codes", [])}):
            reason_codes.append(code)
    decision = "HYP004_EXPLORATION_PASS" if selection_ok and pass_candidates else "HYP004_EXPLORATION_BLOCK"
    approved_for_research = decision == "HYP004_EXPLORATION_PASS"
    return {
        "contract_version": HYP004_EXPLORATION_CONTRACT_VERSION,
        "phase": "25O",
        "report_type": "hyp004_cross_symbol_relative_strength_exploration_gate",
        "generated_at": generated_at or utc_now_iso(),
        "decision": decision,
        "ok": approved_for_research,
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "source": source,
        "symbols": list(prices.columns),
        "bar_count": int(prices.shape[0]),
        "candidate_count": len(candidates),
        "passed_candidate_count": len(pass_candidates),
        "selected_candidate": selected,
        "candidates": candidates,
        "limits": asdict(limits),
        "reason_codes": sorted(set(reason_codes)),
        "recommendation": (
            "HYP-004 produced a research-only cross-symbol relative strength candidate. Do not train, reload, paper trade, or enable live trading; move to robustness confirmation first."
            if approved_for_research
            else "No HYP-004 relative-strength candidate passed exploration. Do not train, reload, paper trade, or enable live trading; refine or close this hypothesis."
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
    selected = report.get("selected_candidate") or {}
    metrics = selected.get("metrics") if isinstance(selected, Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25O HYP-004 Cross-Symbol Relative Strength Exploration Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- symbols: `{', '.join(report.get('symbols', []))}`",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- passed_candidate_count: `{report.get('passed_candidate_count')}`",
        f"- selected_strategy_family: `{selected.get('strategy_family') if isinstance(selected, Mapping) else None}`",
        f"- selected_signal_count: `{metrics.get('signal_count') if isinstance(metrics, Mapping) else None}`",
        f"- selected_mean_net_edge_bps: `{metrics.get('mean_net_edge_bps') if isinstance(metrics, Mapping) else None}`",
        f"- selected_median_net_edge_bps: `{metrics.get('median_net_edge_bps') if isinstance(metrics, Mapping) else None}`",
        f"- selected_profit_factor: `{metrics.get('profit_factor') if isinstance(metrics, Mapping) else None}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Candidates",
        "",
        "| strategy | decision | score | signals | mean | median | pf | oos | wf+ | dom_sym | top_win | reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for candidate in report.get("candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        m = candidate.get("metrics", {}) if isinstance(candidate.get("metrics"), Mapping) else {}
        lines.append(
            f"| {candidate.get('strategy_family')} | {candidate.get('decision')} | {candidate.get('score')} | {m.get('signal_count')} | "
            f"{m.get('mean_net_edge_bps')} | {m.get('median_net_edge_bps')} | {m.get('profit_factor')} | {m.get('oos_mean_net_edge_bps')} | "
            f"{m.get('walk_forward_positive_rate_pct')} | {m.get('dominant_symbol_pct')} | {m.get('top_win_dependency_pct')} | `{candidate.get('reason_codes')}` |"
        )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- No model training.",
        "- No model reload.",
        "- No config mutation.",
        "- No paper trading.",
        "- No live trading.",
        "- No order actions.",
    ])
    return "\n".join(lines) + "\n"
