from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

HYP005_EXPLORATION_CONTRACT_VERSION = "4B.4.3.6.6.25S"
REPORT_PREFIX = "4B436625S_hyp005_liquidity_sweep_reversal_exploration"
HYPOTHESIS_ID = "HYP-005"
BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass(frozen=True)
class LiquiditySweepStrategySpec:
    name: str
    lookback_bars: int
    hold_bars: int
    min_sweep_bps: float
    min_wick_pct: float
    compression_window: int = 12
    compression_baseline_bars: int = 48
    max_compression_ratio: float = 0.85
    diagnostic_only: bool = False


@dataclass(frozen=True)
class LiquiditySweepExplorationLimits:
    min_signal_count: int = 24
    min_mean_net_edge_bps: float = 8.0
    min_median_net_edge_bps: float = 4.0
    min_profit_factor: float = 1.18
    min_win_rate_pct: float = 48.0
    min_oos_mean_net_edge_bps: float = 0.0
    min_walk_forward_positive_rate_pct: float = 55.0
    max_dominant_symbol_pct: float = 76.0
    max_top_win_dependency_pct: float = 38.0
    max_wick_dependency_pct: float = 88.0
    min_symbols_traded: int = 2
    round_trip_cost_bps: float = 16.0


DEFAULT_STRATEGIES: tuple[LiquiditySweepStrategySpec, ...] = (
    LiquiditySweepStrategySpec(
        "long_liquidity_sweep_reversal",
        lookback_bars=24,
        hold_bars=6,
        min_sweep_bps=18.0,
        min_wick_pct=42.0,
        max_compression_ratio=1.05,
    ),
    LiquiditySweepStrategySpec(
        "short_liquidity_sweep_reversal",
        lookback_bars=24,
        hold_bars=6,
        min_sweep_bps=18.0,
        min_wick_pct=42.0,
        max_compression_ratio=1.05,
    ),
    LiquiditySweepStrategySpec(
        "compression_sweep_reversal",
        lookback_bars=36,
        hold_bars=8,
        min_sweep_bps=22.0,
        min_wick_pct=48.0,
        max_compression_ratio=0.82,
    ),
    LiquiditySweepStrategySpec(
        "compression_breakout_fakeout_probe",
        lookback_bars=18,
        hold_bars=4,
        min_sweep_bps=14.0,
        min_wick_pct=35.0,
        max_compression_ratio=0.92,
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


def validate_hyp005_selection(report: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    if not report:
        return False, ["HYP005_SELECTION_REPORT_MISSING"]
    selected_id = str(
        report.get("selected_next_hypothesis_id")
        or report.get("hypothesis_id")
        or report.get("selected_hypothesis_id")
        or ""
    )
    decision = str(report.get("decision") or "")
    if selected_id != HYPOTHESIS_ID:
        return False, ["HYP005_NOT_SELECTED"]
    if decision not in {"NEXT_HYPOTHESIS_SELECTED", "HYP005_SELECTED", "REGISTRY_READY"}:
        return False, ["HYP005_SELECTION_DECISION_INVALID"]
    return True, []


def normalize_market_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "open_time", "open", "high", "low", "close"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"market frame missing required columns: {missing}")
    out = df.copy()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["open_time"] = pd.to_numeric(out["open_time"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["symbol", "open_time", "open", "high", "low", "close"])
    out = out.sort_values(["symbol", "open_time"]).reset_index(drop=True)
    if out.empty:
        raise ValueError("market frame has no usable rows")
    if out["symbol"].nunique() < 1:
        raise ValueError("at least one symbol is required for HYP-005 exploration")
    return out


def _true_range(frame: pd.DataFrame) -> pd.Series:
    prev_close = frame["close"].shift(1)
    ranges = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _prepared_symbol_frame(frame: pd.DataFrame, spec: LiquiditySweepStrategySpec) -> pd.DataFrame:
    out = frame.sort_values("open_time").copy()
    out["prev_range_high"] = out["high"].rolling(spec.lookback_bars, min_periods=spec.lookback_bars).max().shift(1)
    out["prev_range_low"] = out["low"].rolling(spec.lookback_bars, min_periods=spec.lookback_bars).min().shift(1)
    candle_range = (out["high"] - out["low"]).replace(0.0, np.nan)
    out["lower_wick_pct"] = ((out[["open", "close"]].min(axis=1) - out["low"]) / candle_range * 100.0).clip(lower=0.0)
    out["upper_wick_pct"] = ((out["high"] - out[["open", "close"]].max(axis=1)) / candle_range * 100.0).clip(lower=0.0)
    tr = _true_range(out)
    short_tr = tr.rolling(spec.compression_window, min_periods=max(3, spec.compression_window // 2)).mean().shift(1)
    long_tr = tr.rolling(spec.compression_baseline_bars, min_periods=max(6, spec.compression_baseline_bars // 3)).mean().shift(1)
    out["compression_ratio"] = (short_tr / long_tr).replace([np.inf, -np.inf], np.nan)
    out["future_return_bps"] = ((out["close"].shift(-spec.hold_bars) / out["close"]) - 1.0) * 10_000.0
    out["sweep_down_bps"] = ((out["prev_range_low"] - out["low"]) / out["prev_range_low"]) * 10_000.0
    out["sweep_up_bps"] = ((out["high"] - out["prev_range_high"]) / out["prev_range_high"]) * 10_000.0
    return out


def _edge_row(
    row: pd.Series,
    *,
    symbol: str,
    side: str,
    edge_bps: float,
    spec: LiquiditySweepStrategySpec,
    sweep_bps: float,
    wick_pct: float,
) -> dict[str, Any]:
    return {
        "open_time": int(row["open_time"]),
        "symbol": symbol,
        "side": side,
        "strategy_family": spec.name,
        "lookback_bars": spec.lookback_bars,
        "hold_bars": spec.hold_bars,
        "sweep_bps": round(float(sweep_bps), 6),
        "wick_pct": round(float(wick_pct), 6),
        "compression_ratio": round(safe_float(row.get("compression_ratio"), 999.0), 6),
        "net_edge_bps": round(float(edge_bps), 6),
    }


def strategy_edges_for_symbol(frame: pd.DataFrame, spec: LiquiditySweepStrategySpec, cost_bps: float) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    symbol = str(frame["symbol"].iloc[0]).upper()
    data = _prepared_symbol_frame(frame, spec)
    rows: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        if any(pd.isna(row.get(col)) for col in ("prev_range_high", "prev_range_low", "future_return_bps")):
            continue
        compression_ratio = safe_float(row.get("compression_ratio"), 999.0)
        compression_ok = compression_ratio <= spec.max_compression_ratio
        long_sweep = (
            safe_float(row.get("sweep_down_bps")) >= spec.min_sweep_bps
            and safe_float(row.get("lower_wick_pct")) >= spec.min_wick_pct
            and safe_float(row.get("close")) > safe_float(row.get("prev_range_low"))
        )
        short_sweep = (
            safe_float(row.get("sweep_up_bps")) >= spec.min_sweep_bps
            and safe_float(row.get("upper_wick_pct")) >= spec.min_wick_pct
            and safe_float(row.get("close")) < safe_float(row.get("prev_range_high"))
        )
        if spec.name == "long_liquidity_sweep_reversal":
            if long_sweep and compression_ok:
                edge = safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=BUY, edge_bps=edge, spec=spec, sweep_bps=row["sweep_down_bps"], wick_pct=row["lower_wick_pct"]))
        elif spec.name == "short_liquidity_sweep_reversal":
            if short_sweep and compression_ok:
                edge = -safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=SELL, edge_bps=edge, spec=spec, sweep_bps=row["sweep_up_bps"], wick_pct=row["upper_wick_pct"]))
        elif spec.name == "compression_sweep_reversal":
            if not compression_ok:
                continue
            if long_sweep:
                edge = safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=BUY, edge_bps=edge, spec=spec, sweep_bps=row["sweep_down_bps"], wick_pct=row["lower_wick_pct"]))
            elif short_sweep:
                edge = -safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=SELL, edge_bps=edge, spec=spec, sweep_bps=row["sweep_up_bps"], wick_pct=row["upper_wick_pct"]))
        elif spec.name == "compression_breakout_fakeout_probe":
            # Diagnostic: loose fakeout detector. It is intentionally not approvable.
            if not compression_ok:
                continue
            if long_sweep:
                edge = safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=BUY, edge_bps=edge, spec=spec, sweep_bps=row["sweep_down_bps"], wick_pct=row["lower_wick_pct"]))
            elif short_sweep:
                edge = -safe_float(row["future_return_bps"]) - cost_bps
                rows.append(_edge_row(row, symbol=symbol, side=SELL, edge_bps=edge, spec=spec, sweep_bps=row["sweep_up_bps"], wick_pct=row["upper_wick_pct"]))
        else:
            raise ValueError(f"unsupported HYP-005 strategy family: {spec.name}")
    return pd.DataFrame(rows)


def strategy_edges(df: pd.DataFrame, spec: LiquiditySweepStrategySpec, cost_bps: float) -> pd.DataFrame:
    normalized = normalize_market_frame(df)
    frames = [strategy_edges_for_symbol(group, spec, cost_bps) for _, group in normalized.groupby("symbol", sort=True)]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["open_time", "symbol"]).reset_index(drop=True)


def split_dataframe(df: pd.DataFrame, parts: int) -> list[pd.DataFrame]:
    if df.empty:
        return []
    indexes = np.array_split(np.arange(len(df)), max(1, int(parts)))
    return [df.iloc[idx].copy() for idx in indexes if len(idx) > 0]


def summarize_edges(edges: pd.DataFrame, *, limits: LiquiditySweepExplorationLimits) -> dict[str, Any]:
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
            "wick_dependency_pct": 100.0,
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
    wick = pd.to_numeric(edges.get("wick_pct", pd.Series(dtype=float)), errors="coerce").dropna()
    wick_dependency_pct = float((wick >= wick.quantile(0.75)).mean() * 100.0) if not wick.empty else 100.0
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
        "wick_dependency_pct": round(wick_dependency_pct, 6),
        "symbols_traded": int(symbol_counts.shape[0]),
    }


def evaluate_candidate(spec: LiquiditySweepStrategySpec, edges: pd.DataFrame, *, limits: LiquiditySweepExplorationLimits) -> dict[str, Any]:
    metrics = summarize_edges(edges, limits=limits)
    reasons: list[str] = []
    warnings: list[str] = []
    if spec.diagnostic_only:
        reasons.append("DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if metrics["signal_count"] < limits.min_signal_count:
        reasons.append("HYP005_SIGNAL_COUNT_LOW")
    if metrics["mean_net_edge_bps"] < limits.min_mean_net_edge_bps:
        reasons.append("HYP005_MEAN_EDGE_LOW")
    if metrics["median_net_edge_bps"] < limits.min_median_net_edge_bps:
        reasons.append("HYP005_MEDIAN_EDGE_LOW")
    if metrics["profit_factor"] < limits.min_profit_factor:
        reasons.append("HYP005_PROFIT_FACTOR_LOW")
    if metrics["win_rate_pct"] < limits.min_win_rate_pct:
        reasons.append("HYP005_WIN_RATE_LOW")
    if metrics["oos_mean_net_edge_bps"] < limits.min_oos_mean_net_edge_bps:
        reasons.append("HYP005_OOS_EDGE_LOW")
    if metrics["walk_forward_positive_rate_pct"] < limits.min_walk_forward_positive_rate_pct:
        reasons.append("HYP005_WALK_FORWARD_STABILITY_LOW")
    if metrics["dominant_symbol_pct"] > limits.max_dominant_symbol_pct:
        reasons.append("HYP005_DOMINANT_SYMBOL_DEPENDENCY_HIGH")
    if metrics["top_win_dependency_pct"] > limits.max_top_win_dependency_pct:
        reasons.append("HYP005_TOP_WIN_DEPENDENCY_HIGH")
    if metrics["wick_dependency_pct"] > limits.max_wick_dependency_pct:
        warnings.append("HYP005_WICK_DEPENDENCY_ELEVATED")
    if metrics["symbols_traded"] < limits.min_symbols_traded:
        reasons.append("HYP005_SYMBOL_DIVERSITY_LOW")
    score = (
        metrics["mean_net_edge_bps"]
        + metrics["median_net_edge_bps"] * 0.75
        + metrics["oos_mean_net_edge_bps"] * 0.5
        + metrics["profit_factor"] * 8.0
        + metrics["walk_forward_positive_rate_pct"] * 0.12
        - metrics["top_win_dependency_pct"] * 0.2
        - metrics["dominant_symbol_pct"] * 0.08
    )
    return {
        "strategy_family": spec.name,
        "spec": asdict(spec),
        "decision": "PASS" if not reasons else "BLOCK",
        "ok": not reasons,
        "score": round(float(score), 6),
        "metrics": metrics,
        "reason_codes": reasons,
        "warnings": warnings,
        "approved_for_research_candidate": not reasons,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "edge_sample_count": int(len(edges)),
    }


def select_best_candidate(candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            1 if item.get("decision") == "PASS" else 0,
            safe_float(item.get("score")),
            safe_float((item.get("metrics") or {}).get("signal_count")),
        ),
        reverse=True,
    )[0]


def build_hyp005_liquidity_sweep_reversal_exploration_report(
    market_df: pd.DataFrame,
    *,
    selection_report: Mapping[str, Any] | None = None,
    source: str = "unknown",
    limits: LiquiditySweepExplorationLimits | None = None,
    strategies: Sequence[LiquiditySweepStrategySpec] = DEFAULT_STRATEGIES,
) -> dict[str, Any]:
    limits = limits or LiquiditySweepExplorationLimits()
    selection_ok, selection_reasons = validate_hyp005_selection(selection_report)
    normalized = normalize_market_frame(market_df)
    candidates: list[dict[str, Any]] = []
    for spec in strategies:
        edges = strategy_edges(normalized, spec, limits.round_trip_cost_bps)
        candidates.append(evaluate_candidate(spec, edges, limits=limits))
    selected = select_best_candidate(candidates)
    passed = [candidate for candidate in candidates if candidate.get("decision") == "PASS"]
    reason_codes: list[str] = []
    if not selection_ok:
        reason_codes.extend(selection_reasons)
    if not passed:
        reason_codes.append("NO_HYP005_LIQUIDITY_SWEEP_CANDIDATE_PASSED")
        if selected:
            reason_codes.extend(str(code) for code in selected.get("reason_codes", []))
    decision = "HYP005_EXPLORATION_PASS" if selection_ok and passed else "HYP005_EXPLORATION_BLOCK"
    approved = decision == "HYP005_EXPLORATION_PASS"
    symbols = sorted(normalized["symbol"].astype(str).unique().tolist())
    report = {
        "contract_version": HYP005_EXPLORATION_CONTRACT_VERSION,
        "phase": "25S",
        "report_type": "hyp005_liquidity_sweep_reversal_exploration_gate",
        "generated_at": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "source": source,
        "symbols": symbols,
        "decision": decision,
        "ok": approved,
        "candidate_count": len(candidates),
        "passed_candidate_count": len(passed),
        "selected_candidate": selected,
        "candidates": candidates,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted({warning for candidate in candidates for warning in candidate.get("warnings", [])}),
        "recommendation": (
            "HYP-005 produced a research-only liquidity sweep reversal candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated robustness gate first."
            if approved
            else "No HYP-005 liquidity-sweep reversal candidate passed exploration. Do not train, reload, paper trade, or enable live trading; refine or close this hypothesis."
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


def load_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON report must be an object: {p}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return p


def report_to_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selected_candidate") or {}
    metrics = selected.get("metrics", {}) if isinstance(selected, Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25S HYP-005 Liquidity Sweep Reversal Exploration Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- source: `{report.get('source')}`",
        f"- symbols: `{','.join(report.get('symbols', []))}`",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- passed_candidate_count: `{report.get('passed_candidate_count')}`",
        f"- selected_strategy_family: `{selected.get('strategy_family') if isinstance(selected, Mapping) else None}`",
        f"- selected_signal_count: `{metrics.get('signal_count')}`",
        f"- selected_mean_net_edge_bps: `{metrics.get('mean_net_edge_bps')}`",
        f"- selected_median_net_edge_bps: `{metrics.get('median_net_edge_bps')}`",
        f"- selected_profit_factor: `{metrics.get('profit_factor')}`",
        f"- selected_oos_mean_net_edge_bps: `{metrics.get('oos_mean_net_edge_bps')}`",
        f"- selected_walk_forward_positive_rate_pct: `{metrics.get('walk_forward_positive_rate_pct')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Candidates",
        "",
        "| strategy | decision | score | signals | mean | median | PF | OOS | WF+ | reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for candidate in report.get("candidates", []):
        m = candidate.get("metrics", {}) if isinstance(candidate, Mapping) else {}
        lines.append(
            "| {strategy} | {decision} | {score} | {signals} | {mean} | {median} | {pf} | {oos} | {wf} | `{reasons}` |".format(
                strategy=candidate.get("strategy_family"),
                decision=candidate.get("decision"),
                score=candidate.get("score"),
                signals=m.get("signal_count"),
                mean=m.get("mean_net_edge_bps"),
                median=m.get("median_net_edge_bps"),
                pf=m.get("profit_factor"),
                oos=m.get("oos_mean_net_edge_bps"),
                wf=m.get("walk_forward_positive_rate_pct"),
                reasons=candidate.get("reason_codes", []),
            )
        )
    lines.extend([
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
    ])
    return "\n".join(lines) + "\n"
