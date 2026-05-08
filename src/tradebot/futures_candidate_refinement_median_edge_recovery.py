from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

FUTURES_REFINEMENT_CONTRACT_VERSION = "4B.4.3.6.6.25E"
REPORT_TYPE = "futures_candidate_refinement_median_edge_recovery"
REPORT_PREFIX = "4B436625E_futures_candidate_refinement_median_edge_recovery"

BUY_CLASS = "BUY"
SELL_CLASS = "SELL"
HOLD_CLASS = "HOLD"


@dataclass(frozen=True)
class FuturesRefinementSpec:
    symbol: str = "BTCUSDT"
    interval: str = "4h"
    strategy: str = "funding_trend_exhaustion"
    source_phase: str = "4B.4.3.6.6.25D"
    horizon_bars: int = 1
    round_trip_cost_bps: float = 16.0
    min_edge_bps: float = 0.0


@dataclass(frozen=True)
class MedianEdgeFilterSpec:
    name: str
    min_abs_funding_z: float = 0.0
    min_abs_funding_rate: float = 0.0
    require_oi_alignment: bool = False
    require_taker_confirmation: bool = False
    require_price_trend_alignment: bool = False
    max_abs_vwap_distance_bps: float | None = None
    require_positive_prior_return_against_side: bool = False
    approvable: bool = True
    family: str = "median_edge_refinement"


@dataclass(frozen=True)
class MedianEdgeRecoveryLimits:
    min_signal_count: int = 30
    min_coverage_pct: float = 0.35
    max_coverage_pct: float = 12.0
    max_dominant_side_pct: float = 80.0
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.15
    min_win_rate_pct: float = 48.0
    max_drawdown_pct: float = 25.0
    min_walk_forward_positive_rate_pct: float = 60.0
    max_top_win_dependency_pct: float = 55.0
    min_oos_edge_bps: float = 0.0


def default_filter_specs() -> list[MedianEdgeFilterSpec]:
    return [
        MedianEdgeFilterSpec("diagnostic_base_candidate", approvable=False, family="diagnostic"),
        MedianEdgeFilterSpec("funding_extreme_strict", min_abs_funding_z=1.0, min_abs_funding_rate=0.00005),
        MedianEdgeFilterSpec("funding_extreme_oi_confirmed", min_abs_funding_z=0.75, require_oi_alignment=True),
        MedianEdgeFilterSpec("funding_extreme_taker_confirmed", min_abs_funding_z=0.75, require_taker_confirmation=True),
        MedianEdgeFilterSpec("funding_extreme_trend_aligned", min_abs_funding_z=0.75, require_price_trend_alignment=True),
        MedianEdgeFilterSpec(
            "funding_oi_taker_guarded",
            min_abs_funding_z=0.6,
            require_oi_alignment=True,
            require_taker_confirmation=True,
        ),
        MedianEdgeFilterSpec(
            "median_edge_recovery_guarded",
            min_abs_funding_z=0.5,
            require_oi_alignment=True,
            require_taker_confirmation=True,
            require_price_trend_alignment=True,
            max_abs_vwap_distance_bps=180.0,
        ),
        MedianEdgeFilterSpec(
            "exhaustion_reversal_guarded",
            min_abs_funding_z=0.5,
            require_oi_alignment=True,
            require_positive_prior_return_against_side=True,
            max_abs_vwap_distance_bps=220.0,
        ),
    ]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        out = float(value)
        return out if isfinite(out) else default
    except Exception:
        return default


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0 or not isfinite(denominator):
        return default
    return numerator / denominator


def _series(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype="float64")


def _zscore(values: pd.Series, window: int = 48) -> pd.Series:
    mean = values.rolling(window=window, min_periods=max(5, window // 4)).mean()
    std = values.rolling(window=window, min_periods=max(5, window // 4)).std(ddof=0)
    return ((values - mean) / std.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def normalize_futures_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    aliases = {
        "openTime": "open_time",
        "timestamp": "open_time",
        "time": "open_time",
        "funding_rate": "fundingRate",
        "sum_open_interest": "sumOpenInterest",
        "open_interest": "sumOpenInterest",
        "long_short_ratio": "longShortRatio",
        "buy_sell_ratio": "buySellRatio",
        "buySellRatio": "buySellRatio",
        "buyVol": "buyVol",
        "sellVol": "sellVol",
    }
    out = out.rename(columns={k: v for k, v in aliases.items() if k in out.columns})
    for required in ["open", "high", "low", "close"]:
        if required not in out.columns:
            raise ValueError(f"missing required OHLC column: {required}")
        out[required] = pd.to_numeric(out[required], errors="coerce")
    if "volume" not in out.columns:
        out["volume"] = 0.0
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)
    for optional in ["fundingRate", "sumOpenInterest", "longShortRatio", "buySellRatio", "buyVol", "sellVol"]:
        if optional in out.columns:
            out[optional] = pd.to_numeric(out[optional], errors="coerce")
    if "open_time" in out.columns:
        out = out.sort_values("open_time")
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return out


def build_refinement_features(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_futures_dataframe(df)
    if out.empty:
        return out
    close = _series(out, "close")
    high = _series(out, "high")
    low = _series(out, "low")
    funding = _series(out, "fundingRate")
    oi = _series(out, "sumOpenInterest")
    long_short = _series(out, "longShortRatio", 1.0)
    buy_sell = _series(out, "buySellRatio", 1.0)

    out["ema_fast"] = close.ewm(span=9, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=21, adjust=False).mean()
    out["trend_sign"] = np.sign(out["ema_fast"] - out["ema_slow"])
    out["vwap_proxy"] = ((high + low + close) / 3.0).rolling(21, min_periods=3).mean()
    out["vwap_distance_bps"] = ((close / out["vwap_proxy"].replace(0, np.nan)) - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0) * 10000.0
    out["funding_z"] = _zscore(funding, 42)
    out["funding_abs"] = funding.abs()
    out["oi_change_pct"] = oi.pct_change(3).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out["long_short_z"] = _zscore(long_short, 42)
    out["taker_bias"] = (buy_sell - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out["prior_return_bps"] = close.pct_change(3).replace([np.inf, -np.inf], np.nan).fillna(0.0) * 10000.0
    return out


def build_base_funding_trend_exhaustion_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = build_refinement_features(df)
    if out.empty:
        return out.assign(base_signal=False, side=HOLD_CLASS)
    funding_z = _series(out, "funding_z")
    trend = _series(out, "trend_sign")
    # Exhaustion: high positive funding in up-trend -> contrarian SELL.
    # Low/negative funding in down-trend -> contrarian BUY.
    sell = (funding_z > 0.35) & (trend >= 0)
    buy = (funding_z < -0.35) & (trend <= 0)
    side = np.where(buy, BUY_CLASS, np.where(sell, SELL_CLASS, HOLD_CLASS))
    out["base_signal"] = buy | sell
    out["side"] = side
    return out


def apply_filter(signals: pd.DataFrame, filter_spec: MedianEdgeFilterSpec) -> pd.DataFrame:
    if signals.empty:
        return signals.copy()
    out = signals.copy()
    mask = out["base_signal"].astype(bool)
    if filter_spec.min_abs_funding_z > 0:
        mask &= _series(out, "funding_z").abs() >= filter_spec.min_abs_funding_z
    if filter_spec.min_abs_funding_rate > 0:
        mask &= _series(out, "fundingRate").abs() >= filter_spec.min_abs_funding_rate
    side_sign = pd.Series(np.where(out["side"] == BUY_CLASS, 1.0, np.where(out["side"] == SELL_CLASS, -1.0, 0.0)), index=out.index)
    if filter_spec.require_oi_alignment:
        # For exhaustion reversal, prefer crowding + OI build-up before reversal.
        mask &= _series(out, "oi_change_pct") > 0
    if filter_spec.require_taker_confirmation:
        # Prefer flow already leaning into the reversal direction.
        mask &= (side_sign * _series(out, "taker_bias")) > 0
    if filter_spec.require_price_trend_alignment:
        # In reversal candidate, side is contrarian to current trend but should have a meaningful trend backdrop.
        mask &= (side_sign * _series(out, "trend_sign")) <= 0
    if filter_spec.max_abs_vwap_distance_bps is not None:
        mask &= _series(out, "vwap_distance_bps").abs() <= float(filter_spec.max_abs_vwap_distance_bps)
    if filter_spec.require_positive_prior_return_against_side:
        # Reversal needs prior move against the trade direction.
        mask &= (side_sign * _series(out, "prior_return_bps")) < 0
    out["refined_signal"] = mask
    return out


def _max_drawdown_pct(net_edges_bps: Sequence[float]) -> float:
    if not net_edges_bps:
        return 0.0
    equity = np.cumsum(np.asarray(net_edges_bps, dtype="float64")) / 10000.0
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    return float(np.max(drawdown) * 100.0) if len(drawdown) else 0.0


def _profit_factor(net_edges_bps: Sequence[float]) -> float:
    arr = np.asarray(net_edges_bps, dtype="float64")
    wins = float(arr[arr > 0].sum())
    losses = float(abs(arr[arr < 0].sum()))
    if wins <= 0 and losses <= 0:
        return 0.0
    if losses == 0:
        return 99.0
    return wins / losses


def _window_positive_rate(net_edges_bps: Sequence[float], windows: int = 4) -> float:
    arr = np.asarray(net_edges_bps, dtype="float64")
    if len(arr) == 0:
        return 0.0
    chunks = [chunk for chunk in np.array_split(arr, min(windows, len(arr))) if len(chunk)]
    positives = sum(float(chunk.mean()) > 0 for chunk in chunks)
    return 100.0 * positives / len(chunks)


def _top_win_dependency_pct(net_edges_bps: Sequence[float], top_n: int = 3) -> float:
    arr = np.asarray(net_edges_bps, dtype="float64")
    wins = np.sort(arr[arr > 0])[::-1]
    total_wins = float(wins.sum())
    if total_wins <= 0:
        return 100.0
    return 100.0 * float(wins[:top_n].sum()) / total_wins


def _dominant_side_pct(sides: Sequence[str]) -> float:
    sides = [s for s in sides if s in {BUY_CLASS, SELL_CLASS}]
    if not sides:
        return 0.0
    buy = sum(s == BUY_CLASS for s in sides)
    sell = sum(s == SELL_CLASS for s in sides)
    return 100.0 * max(buy, sell) / len(sides)


def _side_counts(sides: Sequence[str]) -> dict[str, int]:
    return {BUY_CLASS: int(sum(s == BUY_CLASS for s in sides)), SELL_CLASS: int(sum(s == SELL_CLASS for s in sides))}


def evaluate_filtered_signals(
    filtered: pd.DataFrame,
    filter_spec: MedianEdgeFilterSpec,
    candidate_spec: FuturesRefinementSpec,
    limits: MedianEdgeRecoveryLimits | None = None,
) -> dict[str, Any]:
    limits = limits or MedianEdgeRecoveryLimits()
    if filtered.empty or "refined_signal" not in filtered.columns:
        candidate_rows = filtered.iloc[0:0].copy()
    else:
        candidate_rows = filtered[filtered["refined_signal"].astype(bool)].copy()
    total_rows = max(1, len(filtered))
    horizon = max(1, int(candidate_spec.horizon_bars))
    close = _series(filtered, "close")
    future_close = close.shift(-horizon)
    rows = candidate_rows.index[candidate_rows.index < len(filtered) - horizon]
    candidate_rows = candidate_rows.loc[rows].copy()
    sides = list(candidate_rows.get("side", pd.Series(dtype="object")))
    side_sign = np.asarray([1.0 if s == BUY_CLASS else -1.0 if s == SELL_CLASS else 0.0 for s in sides], dtype="float64")
    entries = close.loc[candidate_rows.index].to_numpy(dtype="float64") if len(candidate_rows) else np.asarray([], dtype="float64")
    exits = future_close.loc[candidate_rows.index].to_numpy(dtype="float64") if len(candidate_rows) else np.asarray([], dtype="float64")
    gross = side_sign * ((exits / entries) - 1.0) * 10000.0 if len(entries) else np.asarray([], dtype="float64")
    gross = np.nan_to_num(gross, nan=0.0, posinf=0.0, neginf=0.0)
    net = gross - float(candidate_spec.round_trip_cost_bps)
    signal_count = int(len(net))
    coverage_pct = 100.0 * signal_count / total_rows
    mean_edge = float(np.mean(net)) if signal_count else 0.0
    median_edge = float(np.median(net)) if signal_count else 0.0
    win_rate = 100.0 * float(np.mean(net > 0)) if signal_count else 0.0
    profit_factor = _profit_factor(net)
    max_dd = _max_drawdown_pct(list(net))
    walk_rate = _window_positive_rate(list(net))
    oos = float(np.mean(net[int(signal_count * 0.7):])) if signal_count and int(signal_count * 0.7) < signal_count else mean_edge
    dominant_side = _dominant_side_pct(sides)
    top_win_dep = _top_win_dependency_pct(list(net))

    reason_codes: list[str] = []
    warnings: list[str] = []
    if not filter_spec.approvable:
        reason_codes.append("DIAGNOSTIC_FILTER_NOT_APPROVABLE")
    if signal_count < limits.min_signal_count:
        reason_codes.append("REFINEMENT_SIGNAL_COUNT_LOW")
    if coverage_pct < limits.min_coverage_pct:
        reason_codes.append("REFINEMENT_COVERAGE_LOW")
    if coverage_pct > limits.max_coverage_pct:
        reason_codes.append("REFINEMENT_COVERAGE_HIGH")
    if dominant_side > limits.max_dominant_side_pct:
        reason_codes.append("REFINEMENT_SIDE_IMBALANCE_HIGH")
    if mean_edge <= limits.min_mean_net_edge_bps:
        reason_codes.append("REFINEMENT_MEAN_EDGE_LOW")
    if median_edge <= limits.min_median_net_edge_bps:
        reason_codes.append("REFINEMENT_MEDIAN_EDGE_LOW")
    if profit_factor < limits.min_profit_factor:
        reason_codes.append("REFINEMENT_PROFIT_FACTOR_LOW")
    if win_rate < limits.min_win_rate_pct:
        reason_codes.append("REFINEMENT_WIN_RATE_LOW")
    if max_dd > limits.max_drawdown_pct:
        reason_codes.append("REFINEMENT_MAX_DRAWDOWN_HIGH")
    if walk_rate < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("REFINEMENT_WALK_FORWARD_STABILITY_LOW")
    if top_win_dep > limits.max_top_win_dependency_pct:
        reason_codes.append("REFINEMENT_TOP_WIN_DEPENDENCY_HIGH")
    if oos <= limits.min_oos_edge_bps:
        reason_codes.append("REFINEMENT_OOS_EDGE_LOW")
    if signal_count < limits.min_signal_count + 5:
        warnings.append("REFINEMENT_SIGNAL_COUNT_NEAR_FLOOR")
    if mean_edge > 0 and median_edge <= 0:
        warnings.append("MEAN_POSITIVE_BUT_MEDIAN_NEGATIVE")

    decision = "PASS" if not reason_codes else "BLOCK"
    score = (
        mean_edge
        + median_edge * 2.0
        + (profit_factor - 1.0) * 35.0
        + walk_rate * 0.25
        - max(0.0, max_dd - limits.max_drawdown_pct) * 4.0
        - max(0.0, top_win_dep - limits.max_top_win_dependency_pct) * 2.0
        - len(reason_codes) * 30.0
    )
    return {
        "contract_version": FUTURES_REFINEMENT_CONTRACT_VERSION,
        "filter": asdict(filter_spec),
        "decision": decision,
        "ok": decision == "PASS",
        "approved_for_research_candidate": decision == "PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "score": round(float(score), 6),
        "metrics": {
            "signal_count": signal_count,
            "coverage_pct": round(coverage_pct, 6),
            "mean_net_edge_bps": round(mean_edge, 6),
            "median_net_edge_bps": round(median_edge, 6),
            "win_rate_pct": round(win_rate, 6),
            "profit_factor": round(float(profit_factor), 6),
            "max_drawdown_pct": round(max_dd, 6),
            "oos_mean_net_edge_bps": round(float(oos), 6),
            "walk_forward_positive_rate_pct": round(walk_rate, 6),
            "dominant_side_pct": round(dominant_side, 6),
            "top_win_dependency_pct": round(top_win_dep, 6),
            "side_counts": _side_counts(sides),
        },
    }


def derive_spec_from_report(report: Mapping[str, Any]) -> FuturesRefinementSpec:
    # Prefer explicit selected fields; otherwise inspect selection/best candidate/spec blocks.
    selected = report.get("selected") or report.get("selected_candidate") or {}
    if isinstance(selected, Mapping):
        symbol = str(selected.get("symbol") or report.get("selected_symbol") or "BTCUSDT")
        interval = str(selected.get("interval") or report.get("selected_interval") or "4h")
        strategy = str(selected.get("strategy") or report.get("selected_strategy") or "funding_trend_exhaustion")
    else:
        symbol = str(report.get("selected_symbol") or report.get("symbol") or "BTCUSDT")
        interval = str(report.get("selected_interval") or report.get("interval") or "4h")
        strategy = str(report.get("selected_strategy") or report.get("strategy") or "funding_trend_exhaustion")
    if "selection" in report and isinstance(report["selection"], Mapping):
        best = report["selection"].get("best_candidate")
        if isinstance(best, Mapping):
            symbol = str(best.get("symbol") or symbol)
            interval = str(best.get("interval") or interval)
            strategy = str(best.get("strategy") or strategy)
    return FuturesRefinementSpec(symbol=symbol, interval=interval, strategy=strategy)


def build_futures_candidate_refinement_report(
    df: pd.DataFrame,
    candidate_spec: FuturesRefinementSpec | None = None,
    filter_specs: Sequence[MedianEdgeFilterSpec] | None = None,
    limits: MedianEdgeRecoveryLimits | None = None,
    source: str = "dataframe",
) -> dict[str, Any]:
    candidate_spec = candidate_spec or FuturesRefinementSpec()
    filter_specs = list(filter_specs or default_filter_specs())
    limits = limits or MedianEdgeRecoveryLimits()
    base = build_base_funding_trend_exhaustion_signals(df)
    candidates = [evaluate_filtered_signals(apply_filter(base, fs), fs, candidate_spec, limits) for fs in filter_specs]
    candidates = sorted(candidates, key=lambda item: float(item.get("score", -999999)), reverse=True)
    passed = [c for c in candidates if c.get("decision") == "PASS"]
    selected = passed[0] if passed else (candidates[0] if candidates else None)
    decision = "PASS" if passed else "BLOCK"
    reason_codes: list[str] = []
    if decision == "BLOCK":
        reason_codes.append("NO_MEDIAN_EDGE_REFINEMENT_CANDIDATE_PASSED")
        if selected:
            reason_codes.extend(str(x) for x in selected.get("reason_codes", []))
    else:
        reason_codes.append("MEDIAN_EDGE_REFINEMENT_CONFIRMED")

    return {
        "contract_version": FUTURES_REFINEMENT_CONTRACT_VERSION,
        "phase": FUTURES_REFINEMENT_CONTRACT_VERSION,
        "report_type": REPORT_TYPE,
        "decision": decision,
        "ok": decision == "PASS",
        "source": source,
        "candidate_spec": asdict(candidate_spec),
        "filter_count": len(candidates),
        "approved_for_research_candidate": decision == "PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "reason_codes": sorted(set(reason_codes)),
        "recommendation": (
            "Median-edge refinement candidate passed. Treat it only as a research candidate; do not train, reload, paper trade, or enable live trading yet."
            if decision == "PASS"
            else "No futures median-edge refinement candidate passed. Do not train, reload, start paper trading, or enable live trading. Tighten the hypothesis or close this candidate."
        ),
        "selected_filter": selected.get("filter", {}).get("name") if selected else None,
        "selected_mean_net_edge_bps": selected.get("metrics", {}).get("mean_net_edge_bps") if selected else 0.0,
        "selected_median_net_edge_bps": selected.get("metrics", {}).get("median_net_edge_bps") if selected else 0.0,
        "selected_profit_factor": selected.get("metrics", {}).get("profit_factor") if selected else 0.0,
        "selected_signal_count": selected.get("metrics", {}).get("signal_count") if selected else 0,
        "selected": selected,
        "candidates": candidates,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
    }


def report_to_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 4B.4.3.6.6.25E Futures Candidate Refinement / Median Edge Recovery")
    lines.append("")
    for key in [
        "contract_version",
        "decision",
        "source",
        "filter_count",
        "approved_for_research_candidate",
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "selected_filter",
        "selected_mean_net_edge_bps",
        "selected_median_net_edge_bps",
        "selected_profit_factor",
        "selected_signal_count",
        "recommendation",
    ]:
        if key in report:
            value = report[key]
            if key == "decision":
                lines.append(f"- {key}: **{value}**")
            else:
                lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    for key, value in dict(report.get("guardrails", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Candidate Spec")
    lines.append("")
    for key, value in dict(report.get("candidate_spec", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Filters")
    lines.append("")
    lines.append("| # | decision | score | filter | signals | coverage_pct | mean_edge_bps | median_edge_bps | win_rate_pct | profit_factor | max_dd_pct | walk_pos_pct | top_win_dep_pct | reasons | warnings |")
    lines.append("|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for idx, candidate in enumerate(report.get("candidates", []), 1):
        metrics = candidate.get("metrics", {})
        filt = candidate.get("filter", {})
        lines.append(
            "| {idx} | {decision} | {score} | {name} | {signals} | {coverage} | {mean} | {median} | {win} | {pf} | {dd} | {walk} | {topdep} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=candidate.get("decision"),
                score=candidate.get("score"),
                name=filt.get("name"),
                signals=metrics.get("signal_count"),
                coverage=metrics.get("coverage_pct"),
                mean=metrics.get("mean_net_edge_bps"),
                median=metrics.get("median_net_edge_bps"),
                win=metrics.get("win_rate_pct"),
                pf=metrics.get("profit_factor"),
                dd=metrics.get("max_drawdown_pct"),
                walk=metrics.get("walk_forward_positive_rate_pct"),
                topdep=metrics.get("top_win_dependency_pct"),
                reasons=candidate.get("reason_codes", []),
                warnings=candidate.get("warnings", []),
            )
        )
    lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append(
        "This tool uses public market/futures research data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a refined research candidate; paper/live trading remains blocked."
    )
    return "\n".join(lines) + "\n"
