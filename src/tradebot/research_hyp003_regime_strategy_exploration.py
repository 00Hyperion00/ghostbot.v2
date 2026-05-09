from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

HYP003_EXPLORATION_CONTRACT_VERSION = "4B.4.3.6.6.25J"
REPORT_PREFIX = "4B436625J_hyp003_regime_strategy_exploration"
DEFAULT_HYPOTHESIS_ID = "HYP-003"
DEFAULT_HYPOTHESIS_TITLE = "Regime-specific strategy family"

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass(frozen=True)
class RegimeStrategyExplorationLimits:
    min_clean_rows: int = 250
    min_signal_count: int = 20
    min_regime_signal_count: int = 10
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.12
    min_win_rate_pct: float = 47.0
    min_oos_mean_edge_bps: float = 0.0
    min_walk_forward_positive_rate_pct: float = 50.0
    max_dominant_side_pct: float = 85.0
    max_top_win_dependency_pct: float = 60.0
    max_signal_coverage_pct: float = 45.0
    min_signal_coverage_pct: float = 1.0


@dataclass(frozen=True)
class StrategyFamilySpec:
    name: str
    regime: str
    hold_bars: int
    cost_bps: float = 16.0
    breakout_lookback: int = 20
    range_lookback: int = 24
    pullback_lookback: int = 8
    approvable: bool = True


def default_strategy_specs() -> tuple[StrategyFamilySpec, ...]:
    return (
        StrategyFamilySpec("volatility_expansion_breakout", "high_vol_trend", hold_bars=3, breakout_lookback=18),
        StrategyFamilySpec("trend_pullback_continuation", "trend", hold_bars=4, pullback_lookback=8),
        StrategyFamilySpec("range_mean_reversion", "range", hold_bars=2, range_lookback=24),
        StrategyFamilySpec("low_vol_breakout_probe", "low_vol", hold_bars=4, breakout_lookback=28, approvable=False),
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    if den == 0 or not math.isfinite(den):
        return default
    return num / den


def _series(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype="float64")


def normalize_ohlcv_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    aliases = {
        "openTime": "open_time",
        "timestamp": "open_time",
        "time": "open_time",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = out.rename(columns={old: new for old, new in aliases.items() if old in out.columns})
    for col in ("open", "high", "low", "close"):
        if col not in out.columns:
            raise ValueError(f"missing required OHLC column: {col}")
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if "volume" not in out.columns:
        out["volume"] = 0.0
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)
    if "open_time" in out.columns:
        out = out.sort_values("open_time")
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return out


def build_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_ohlcv_dataframe(df)
    if out.empty:
        return out
    close = _series(out, "close")
    high = _series(out, "high")
    low = _series(out, "low")
    prev_close = close.shift(1).fillna(close)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=3).mean().bfill().fillna(0.0)
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=36, adjust=False).mean()
    returns = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    vol = returns.rolling(30, min_periods=8).std(ddof=0).fillna(0.0) * 10000.0
    trend_bps = ((ema_fast / ema_slow.replace(0, np.nan)) - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0) * 10000.0
    trend_abs = trend_bps.abs()
    trend_q65 = float(trend_abs.quantile(0.65)) if len(trend_abs) else 0.0
    trend_q35 = float(trend_abs.quantile(0.35)) if len(trend_abs) else 0.0
    vol_q65 = float(vol.quantile(0.65)) if len(vol) else 0.0
    vol_q35 = float(vol.quantile(0.35)) if len(vol) else 0.0

    out["atr_14"] = atr
    out["atr_bps"] = (atr / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0) * 10000.0
    out["ema_fast"] = ema_fast
    out["ema_slow"] = ema_slow
    out["trend_bps"] = trend_bps
    out["trend_sign"] = np.sign(trend_bps).replace(0, 0)
    out["realized_vol_bps"] = vol
    out["vol_q65"] = vol_q65
    out["vol_q35"] = vol_q35
    out["trend_q65"] = trend_q65
    out["trend_q35"] = trend_q35

    high_vol = vol >= max(vol_q65, 1e-9)
    low_vol = vol <= max(vol_q35, 1e-9)
    strong_trend = trend_abs >= max(trend_q65, 1e-9)
    weak_trend = trend_abs <= max(trend_q35, 1e-9)
    regimes = np.where(
        high_vol & strong_trend,
        "high_vol_trend",
        np.where(strong_trend, "trend", np.where(low_vol & weak_trend, "low_vol", "range")),
    )
    out["market_regime"] = regimes
    return out


def generate_strategy_signals(features: pd.DataFrame, spec: StrategyFamilySpec) -> pd.Series:
    if features.empty:
        return pd.Series(dtype="object")
    close = _series(features, "close")
    ema_fast = _series(features, "ema_fast")
    ema_slow = _series(features, "ema_slow")
    regime_mask = features["market_regime"].eq(spec.regime)
    if spec.regime == "trend":
        regime_mask = features["market_regime"].isin(["trend", "high_vol_trend"])

    side = pd.Series(HOLD, index=features.index, dtype="object")
    if spec.name == "volatility_expansion_breakout":
        rolling_high = _series(features, "high").rolling(spec.breakout_lookback, min_periods=max(5, spec.breakout_lookback // 3)).max().shift(1)
        rolling_low = _series(features, "low").rolling(spec.breakout_lookback, min_periods=max(5, spec.breakout_lookback // 3)).min().shift(1)
        buy = regime_mask & (close > rolling_high) & (ema_fast >= ema_slow)
        sell = regime_mask & (close < rolling_low) & (ema_fast <= ema_slow)
    elif spec.name == "trend_pullback_continuation":
        recent_low = _series(features, "low").rolling(spec.pullback_lookback, min_periods=3).min()
        recent_high = _series(features, "high").rolling(spec.pullback_lookback, min_periods=3).max()
        buy = regime_mask & (ema_fast > ema_slow) & (close > ema_fast) & (recent_low <= ema_fast)
        sell = regime_mask & (ema_fast < ema_slow) & (close < ema_fast) & (recent_high >= ema_fast)
    elif spec.name == "range_mean_reversion":
        rolling_high = _series(features, "high").rolling(spec.range_lookback, min_periods=max(5, spec.range_lookback // 3)).max()
        rolling_low = _series(features, "low").rolling(spec.range_lookback, min_periods=max(5, spec.range_lookback // 3)).min()
        loc = (close - rolling_low) / (rolling_high - rolling_low).replace(0, np.nan)
        buy = regime_mask & (loc <= 0.18)
        sell = regime_mask & (loc >= 0.82)
    elif spec.name == "low_vol_breakout_probe":
        rolling_high = _series(features, "high").rolling(spec.breakout_lookback, min_periods=max(5, spec.breakout_lookback // 3)).max().shift(1)
        rolling_low = _series(features, "low").rolling(spec.breakout_lookback, min_periods=max(5, spec.breakout_lookback // 3)).min().shift(1)
        buy = regime_mask & (close > rolling_high)
        sell = regime_mask & (close < rolling_low)
    else:
        buy = pd.Series(False, index=features.index)
        sell = pd.Series(False, index=features.index)
    side.loc[buy.fillna(False)] = BUY
    side.loc[sell.fillna(False)] = SELL
    return side


def _profit_factor(edges: Sequence[float]) -> float:
    arr = np.asarray(edges, dtype="float64")
    wins = float(arr[arr > 0].sum())
    losses = float(abs(arr[arr < 0].sum()))
    if wins <= 0 and losses <= 0:
        return 0.0
    if losses == 0:
        return 99.0
    return wins / losses


def _max_drawdown_bps(edges: Sequence[float]) -> float:
    if not edges:
        return 0.0
    equity = np.cumsum(np.asarray(edges, dtype="float64"))
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    return float(np.max(dd)) if len(dd) else 0.0


def _walk_positive_rate(edges: Sequence[float], windows: int = 4) -> float:
    arr = np.asarray(edges, dtype="float64")
    if len(arr) == 0:
        return 0.0
    chunks = [chunk for chunk in np.array_split(arr, min(windows, len(arr))) if len(chunk)]
    return 100.0 * sum(float(chunk.mean()) > 0 for chunk in chunks) / len(chunks)


def _top_win_dependency(edges: Sequence[float], top_n: int = 3) -> float:
    arr = np.asarray(edges, dtype="float64")
    wins = np.sort(arr[arr > 0])[::-1]
    total = float(wins.sum())
    if total <= 0:
        return 100.0
    return 100.0 * float(wins[:top_n].sum()) / total


def _dominant_side_pct(sides: Sequence[str]) -> float:
    actionable = [item for item in sides if item in {BUY, SELL}]
    if not actionable:
        return 0.0
    buy = sum(1 for item in actionable if item == BUY)
    sell = sum(1 for item in actionable if item == SELL)
    return 100.0 * max(buy, sell) / len(actionable)


def evaluate_strategy_candidate(
    df: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    spec: StrategyFamilySpec,
    limits: RegimeStrategyExplorationLimits | None = None,
) -> dict[str, Any]:
    limits = limits or RegimeStrategyExplorationLimits()
    features = build_regime_features(df)
    side = generate_strategy_signals(features, spec)
    close = _series(features, "close")
    horizon = max(1, int(spec.hold_bars))
    entries: list[float] = []
    exits: list[float] = []
    sides: list[str] = []
    regimes: list[str] = []
    for idx, value in side.items():
        if value not in {BUY, SELL}:
            continue
        exit_idx = int(idx) + horizon
        if exit_idx >= len(features):
            continue
        entries.append(float(close.iloc[int(idx)]))
        exits.append(float(close.iloc[exit_idx]))
        sides.append(str(value))
        regimes.append(str(features["market_regime"].iloc[int(idx)]))
    side_sign = np.asarray([1.0 if item == BUY else -1.0 for item in sides], dtype="float64")
    entry_arr = np.asarray(entries, dtype="float64")
    exit_arr = np.asarray(exits, dtype="float64")
    gross = side_sign * ((exit_arr / np.where(entry_arr == 0, np.nan, entry_arr)) - 1.0) * 10000.0 if len(entries) else np.asarray([], dtype="float64")
    gross = np.nan_to_num(gross, nan=0.0, posinf=0.0, neginf=0.0)
    net = gross - float(spec.cost_bps)
    signal_count = int(len(net))
    total_rows = max(1, len(features))
    coverage_pct = 100.0 * signal_count / total_rows
    mean_edge = float(np.mean(net)) if signal_count else 0.0
    median_edge = float(np.median(net)) if signal_count else 0.0
    profit_factor = _profit_factor(net)
    win_rate = 100.0 * float(np.mean(net > 0)) if signal_count else 0.0
    max_dd = _max_drawdown_bps(list(net))
    walk = _walk_positive_rate(list(net))
    oos_start = int(signal_count * 0.7)
    oos_mean = float(np.mean(net[oos_start:])) if signal_count and oos_start < signal_count else mean_edge
    top_dep = _top_win_dependency(list(net))
    dominant_side = _dominant_side_pct(sides)
    reason_codes: list[str] = []
    warnings: list[str] = []
    if not spec.approvable:
        reason_codes.append("DIAGNOSTIC_STRATEGY_FAMILY_NOT_APPROVABLE")
    if len(features) < limits.min_clean_rows:
        reason_codes.append("HYP003_CLEAN_ROWS_LOW")
    if signal_count < limits.min_signal_count:
        reason_codes.append("HYP003_SIGNAL_COUNT_LOW")
    if coverage_pct < limits.min_signal_coverage_pct:
        reason_codes.append("HYP003_SIGNAL_COVERAGE_LOW")
    if coverage_pct > limits.max_signal_coverage_pct:
        reason_codes.append("HYP003_SIGNAL_COVERAGE_HIGH")
    if mean_edge <= limits.min_mean_net_edge_bps:
        reason_codes.append("HYP003_MEAN_EDGE_LOW")
    if median_edge <= limits.min_median_net_edge_bps:
        reason_codes.append("HYP003_MEDIAN_EDGE_LOW")
    if profit_factor < limits.min_profit_factor:
        reason_codes.append("HYP003_PROFIT_FACTOR_LOW")
    if win_rate < limits.min_win_rate_pct:
        reason_codes.append("HYP003_WIN_RATE_LOW")
    if oos_mean <= limits.min_oos_mean_edge_bps:
        reason_codes.append("HYP003_OOS_EDGE_LOW")
    if walk < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("HYP003_WALK_FORWARD_STABILITY_LOW")
    if dominant_side > limits.max_dominant_side_pct:
        reason_codes.append("HYP003_SIDE_IMBALANCE_HIGH")
    if top_dep > limits.max_top_win_dependency_pct:
        reason_codes.append("HYP003_TOP_WIN_DEPENDENCY_HIGH")
    if signal_count and signal_count < limits.min_signal_count + 5:
        warnings.append("HYP003_SIGNAL_COUNT_NEAR_FLOOR")
    decision = "PASS" if not reason_codes else "BLOCK"
    score = (
        mean_edge
        + 1.5 * median_edge
        + 30.0 * (profit_factor - 1.0)
        + 0.2 * walk
        - max(0.0, dominant_side - limits.max_dominant_side_pct) * 2.0
        - len(reason_codes) * 35.0
    )
    return {
        "contract_version": HYP003_EXPLORATION_CONTRACT_VERSION,
        "symbol": symbol,
        "interval": interval,
        "strategy_family": spec.name,
        "regime": spec.regime,
        "decision": decision,
        "ok": decision == "PASS",
        "approved_for_research_candidate": decision == "PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "score": round(float(score), 6),
        "reason_codes": reason_codes,
        "warnings": warnings,
        "spec": asdict(spec),
        "metrics": {
            "clean_rows": int(len(features)),
            "signal_count": signal_count,
            "coverage_pct": round(coverage_pct, 6),
            "mean_net_edge_bps": round(mean_edge, 6),
            "median_net_edge_bps": round(median_edge, 6),
            "profit_factor": round(profit_factor, 6),
            "win_rate_pct": round(win_rate, 6),
            "max_drawdown_bps": round(max_dd, 6),
            "oos_mean_net_edge_bps": round(oos_mean, 6),
            "walk_forward_positive_rate_pct": round(walk, 6),
            "dominant_side_pct": round(dominant_side, 6),
            "top_win_dependency_pct": round(top_dep, 6),
            "buy_count": int(sum(1 for item in sides if item == BUY)),
            "sell_count": int(sum(1 for item in sides if item == SELL)),
            "regime_signal_counts": {regime: int(regimes.count(regime)) for regime in sorted(set(regimes))},
        },
    }


def _selected_hypothesis_from_report(report: Mapping[str, Any]) -> tuple[str, str]:
    hid = str(report.get("selected_next_hypothesis_id") or report.get("hypothesis_id") or "")
    title = str(report.get("selected_next_hypothesis_title") or report.get("hypothesis_title") or "")
    if not hid and isinstance(report.get("selected_next_hypothesis"), Mapping):
        selected = report["selected_next_hypothesis"]
        hid = str(selected.get("hypothesis_id") or selected.get("id") or "")
        title = str(selected.get("title") or selected.get("name") or "")
    return hid, title


def validate_hyp003_selected(input_reports: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    reason_codes: list[str] = []
    if not input_reports:
        reason_codes.append("HYP003_SELECTION_EVIDENCE_NOT_PROVIDED")
        return False, reason_codes
    found = False
    for report in input_reports:
        hid, _ = _selected_hypothesis_from_report(report)
        decision = str(report.get("decision") or "")
        if hid == DEFAULT_HYPOTHESIS_ID and decision in {"NEXT_HYPOTHESIS_SELECTED", ""}:
            found = True
    if not found:
        reason_codes.append("HYP003_NOT_SELECTED_BY_25I")
    return found, reason_codes


def build_hyp003_regime_strategy_exploration_report(
    datasets: Mapping[tuple[str, str], pd.DataFrame],
    *,
    input_reports: Sequence[Mapping[str, Any]] = (),
    strategy_specs: Sequence[StrategyFamilySpec] | None = None,
    limits: RegimeStrategyExplorationLimits | None = None,
    source: str = "dataframe",
) -> dict[str, Any]:
    strategy_specs = tuple(strategy_specs or default_strategy_specs())
    limits = limits or RegimeStrategyExplorationLimits()
    selection_ok, selection_reasons = validate_hyp003_selected(input_reports)
    candidates: list[dict[str, Any]] = []
    for (symbol, interval), df in datasets.items():
        for spec in strategy_specs:
            candidates.append(evaluate_strategy_candidate(df, symbol=symbol, interval=interval, spec=spec, limits=limits))
    candidates.sort(key=lambda item: (item["decision"] == "PASS", item.get("score", -999999)), reverse=True)
    passed = [item for item in candidates if item["decision"] == "PASS"]
    selected = passed[0] if passed else (candidates[0] if candidates else None)
    reason_codes = list(selection_reasons)
    if not datasets:
        reason_codes.append("HYP003_DATASET_MISSING")
    if candidates and not passed:
        reason_codes.append("NO_HYP003_REGIME_STRATEGY_CANDIDATE_PASSED")
        if selected:
            reason_codes.extend(str(code) for code in selected.get("reason_codes", []))
    if passed and selection_ok:
        decision = "HYP003_EXPLORATION_PASS"
        recommendation = "HYP-003 produced a research-only regime strategy candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated robustness gate first."
    else:
        decision = "HYP003_EXPLORATION_BLOCK"
        recommendation = "No approved HYP-003 regime-specific strategy candidate is ready. Do not train, reload, start paper trading, or enable live trading."
    approved_for_research = bool(passed and selection_ok)
    return {
        "contract_version": HYP003_EXPLORATION_CONTRACT_VERSION,
        "phase": "25J",
        "report_type": "hyp003_regime_specific_strategy_family_exploration_gate",
        "decision": decision,
        "ok": decision == "HYP003_EXPLORATION_PASS",
        "source": source,
        "hypothesis_id": DEFAULT_HYPOTHESIS_ID,
        "hypothesis_title": DEFAULT_HYPOTHESIS_TITLE,
        "hypothesis_selected_by_25i": selection_ok,
        "candidate_count": len(candidates),
        "passed_candidate_count": len(passed),
        "selected_candidate": selected,
        "candidates": candidates,
        "reason_codes": sorted(set(reason_codes)) if reason_codes else ["HYP003_RESEARCH_CANDIDATE_IDENTIFIED"],
        "recommendation": recommendation,
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "public_market_data_only": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "training_allowed": False,
            "paper_allowed": False,
            "live_real_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
        "approved_for_research_candidate": approved_for_research,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def report_to_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 4B.4.3.6.6.25J HYP-003 Regime-Specific Strategy Family Exploration Gate")
    lines.append("")
    for key in [
        "contract_version",
        "decision",
        "hypothesis_id",
        "hypothesis_title",
        "hypothesis_selected_by_25i",
        "candidate_count",
        "passed_candidate_count",
        "approved_for_research_candidate",
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "reason_codes",
        "recommendation",
    ]:
        if key in report:
            value = report[key]
            if key == "decision":
                lines.append(f"- {key}: **{value}**")
            else:
                lines.append(f"- {key}: `{value}`")
    selected = report.get("selected_candidate") or {}
    if isinstance(selected, Mapping):
        lines.extend(["", "## Selected Candidate", ""])
        lines.append(f"- symbol: `{selected.get('symbol')}`")
        lines.append(f"- interval: `{selected.get('interval')}`")
        lines.append(f"- strategy_family: `{selected.get('strategy_family')}`")
        lines.append(f"- regime: `{selected.get('regime')}`")
        lines.append(f"- decision: `{selected.get('decision')}`")
        metrics = selected.get("metrics") if isinstance(selected.get("metrics"), Mapping) else {}
        for key in ["signal_count", "mean_net_edge_bps", "median_net_edge_bps", "profit_factor", "oos_mean_net_edge_bps", "walk_forward_positive_rate_pct"]:
            lines.append(f"- {key}: `{metrics.get(key)}`")
    lines.extend(["", "## Candidates", ""])
    lines.append("| # | decision | score | symbol | interval | family | regime | signals | mean | median | pf | oos | reasons |")
    lines.append("|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---:|---|")
    for idx, item in enumerate(report.get("candidates", []), 1):
        metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), Mapping) else {}
        lines.append(
            f"| {idx} | {item.get('decision')} | {item.get('score')} | {item.get('symbol')} | {item.get('interval')} | "
            f"{item.get('strategy_family')} | {item.get('regime')} | {metrics.get('signal_count')} | "
            f"{metrics.get('mean_net_edge_bps')} | {metrics.get('median_net_edge_bps')} | {metrics.get('profit_factor')} | "
            f"{metrics.get('oos_mean_net_edge_bps')} | `{item.get('reason_codes')}` |"
        )
    lines.extend(["", "## Guardrails", ""])
    for key, value in dict(report.get("guardrails", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Policy", "", "This gate never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. A PASS is research-only and must go to a later robustness gate."])
    return "\n".join(lines) + "\n"
