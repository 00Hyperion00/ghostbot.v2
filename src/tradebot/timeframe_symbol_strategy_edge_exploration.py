from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION = "4B.4.3.6.6.24M"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_IDS = (1, 2)


@dataclass(frozen=True, slots=True)
class StrategyEdgeSpec:
    name: str
    family: str = "baseline"
    forward_bars: int | None = None
    approvable: bool = True
    params: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["params"] = dict(self.params or {})
        return payload


@dataclass(frozen=True, slots=True)
class EdgeExplorationLimits:
    min_clean_samples: int = 1_000
    min_signal_count: int = 40
    min_signal_coverage_pct: float = 0.35
    max_signal_coverage_pct: float = 35.0
    max_dominant_action_pct: float = 78.0
    min_mean_net_edge_bps: float = 1.0
    min_median_net_edge_bps: float = -2.0
    min_win_rate_pct: float = 51.0
    min_profit_factor: float = 1.04
    min_edge_lift_bps: float = 3.0
    target_signal_coverage_pct: float = 8.0

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


def _summary(values: Iterable[Any]) -> dict[str, float]:
    vals = sorted(_safe_float(v) for v in values if v is not None and np.isfinite(_safe_float(v)))
    if not vals:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": round(float(vals[0]), 8),
        "median": round(float(median(vals)), 8),
        "mean": round(float(mean(vals)), 8),
        "max": round(float(vals[-1]), 8),
    }


def _class_distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(v, 0) for v in values)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _dominant_action_pct(values: Sequence[int]) -> float:
    counts = Counter(int(v) for v in values if int(v) in ACTION_IDS)
    total = int(counts.get(1, 0) + counts.get(2, 0))
    if total <= 0:
        return 0.0
    return _pct(max(counts.get(1, 0), counts.get(2, 0)), total)


def timeframe_to_minutes(interval: str) -> int:
    cleaned = str(interval).strip().lower()
    if cleaned.endswith("m"):
        return max(int(cleaned[:-1]), 1)
    if cleaned.endswith("h"):
        return max(int(cleaned[:-1]) * 60, 1)
    if cleaned.endswith("d"):
        return max(int(cleaned[:-1]) * 1440, 1)
    return max(int(cleaned), 1)


def default_forward_bars(interval: str) -> int:
    minutes = timeframe_to_minutes(interval)
    if minutes <= 1:
        return 5
    if minutes <= 3:
        return 4
    if minutes <= 5:
        return 3
    if minutes <= 15:
        return 2
    return 1


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"openTime": "open_time", "closeTime": "close_time", "quoteVolume": "quote_volume"}
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    sort_col = "close_time" if "close_time" in out.columns else "open_time"
    out = out.sort_values(sort_col).reset_index(drop=True)
    return out


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0.0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0.0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def add_edge_features(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_ohlcv(df)
    close = pd.to_numeric(out["close"], errors="coerce").astype(float)
    high = pd.to_numeric(out["high"], errors="coerce").astype(float)
    low = pd.to_numeric(out["low"], errors="coerce").astype(float)
    volume = pd.to_numeric(out["volume"], errors="coerce").astype(float)
    out["ema_fast"] = close.ewm(span=9, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=21, adjust=False).mean()
    out["ema_trend"] = close.ewm(span=55, adjust=False).mean()
    out["ema_spread_pct"] = ((out["ema_fast"] - out["ema_slow"]) / close.replace(0.0, np.nan) * 100.0).fillna(0.0)
    out["rsi_14"] = _rsi(close, 14)
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr_14"] = tr.rolling(14, min_periods=1).mean().fillna(0.0)
    out["atr_pct"] = (out["atr_14"] / close.replace(0.0, np.nan) * 100.0).fillna(0.0)
    out["roc_9"] = close.pct_change(9).fillna(0.0) * 100.0
    out["bb_mid"] = close.rolling(20, min_periods=5).mean().fillna(close)
    bb_std = close.rolling(20, min_periods=5).std().fillna(0.0)
    out["bb_upper"] = out["bb_mid"] + (2.0 * bb_std)
    out["bb_lower"] = out["bb_mid"] - (2.0 * bb_std)
    typical = (high + low + close) / 3.0
    # Rolling VWAP avoids session boundary assumptions in cross-timeframe offline research.
    pv = (typical * volume).rolling(60, min_periods=5).sum()
    vv = volume.rolling(60, min_periods=5).sum().replace(0.0, np.nan)
    out["vwap_roll"] = (pv / vv).fillna(close)
    out["close_to_vwap_pct"] = ((close - out["vwap_roll"]) / close.replace(0.0, np.nan) * 100.0).fillna(0.0)
    vol_mean = volume.rolling(30, min_periods=5).mean().replace(0.0, np.nan)
    out["volume_ratio"] = (volume / vol_mean).fillna(1.0)
    out["rolling_high_20"] = high.shift(1).rolling(20, min_periods=5).max().fillna(high)
    out["rolling_low_20"] = low.shift(1).rolling(20, min_periods=5).min().fillna(low)
    out["abs_close_to_vwap_pct"] = out["close_to_vwap_pct"].abs()
    out["trend_flag"] = np.where(out["ema_fast"] > out["ema_slow"], 1, np.where(out["ema_fast"] < out["ema_slow"], -1, 0))
    out["volatility_mid_flag"] = 0
    if len(out) >= 20:
        q25 = float(out["atr_pct"].quantile(0.25))
        q75 = float(out["atr_pct"].quantile(0.75))
        out["volatility_mid_flag"] = np.where((out["atr_pct"] >= q25) & (out["atr_pct"] <= q75), 1, 0)
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def default_strategy_specs() -> list[StrategyEdgeSpec]:
    return [
        StrategyEdgeSpec("trend_following_ema", family="trend", params={"volume_floor": 0.9}),
        StrategyEdgeSpec("trend_pullback_vwap", family="trend", params={"vwap_abs_max": 0.30}),
        StrategyEdgeSpec("vwap_reversion", family="mean_reversion", params={"vwap_abs_min": 0.28}),
        StrategyEdgeSpec("rsi_bollinger_reversion", family="mean_reversion", params={"rsi_buy": 34, "rsi_sell": 66}),
        StrategyEdgeSpec("atr_breakout_volume", family="breakout", params={"volume_floor": 1.15}),
        StrategyEdgeSpec("range_low_vol_reversal", family="range", params={"rsi_buy": 40, "rsi_sell": 60}),
        StrategyEdgeSpec("diagnostic_every_trend_tick", family="diagnostic", approvable=False),
    ]


def _signals_for_strategy(frame: pd.DataFrame, spec: StrategyEdgeSpec) -> pd.Series:
    out = pd.Series(0, index=frame.index, dtype=int)
    params = dict(spec.params or {})
    close = pd.to_numeric(frame.get("close"), errors="coerce").fillna(0.0)
    ema_fast = pd.to_numeric(frame.get("ema_fast"), errors="coerce").fillna(close)
    ema_slow = pd.to_numeric(frame.get("ema_slow"), errors="coerce").fillna(close)
    roc = pd.to_numeric(frame.get("roc_9"), errors="coerce").fillna(0.0)
    rsi = pd.to_numeric(frame.get("rsi_14"), errors="coerce").fillna(50.0)
    volume_ratio = pd.to_numeric(frame.get("volume_ratio"), errors="coerce").fillna(1.0)
    close_to_vwap = pd.to_numeric(frame.get("close_to_vwap_pct"), errors="coerce").fillna(0.0)
    atr = pd.to_numeric(frame.get("atr_14"), errors="coerce").fillna(0.0)
    if spec.name == "trend_following_ema":
        buy = (ema_fast > ema_slow) & (roc > 0.0) & (close > frame["vwap_roll"]) & (volume_ratio >= _safe_float(params.get("volume_floor"), 0.9))
        sell = (ema_fast < ema_slow) & (roc < 0.0) & (close < frame["vwap_roll"]) & (volume_ratio >= _safe_float(params.get("volume_floor"), 0.9))
    elif spec.name == "trend_pullback_vwap":
        near = close_to_vwap.abs() <= _safe_float(params.get("vwap_abs_max"), 0.30)
        buy = (ema_fast > ema_slow) & near & (rsi >= 38.0) & (rsi <= 58.0) & (roc >= -0.08)
        sell = (ema_fast < ema_slow) & near & (rsi >= 42.0) & (rsi <= 62.0) & (roc <= 0.08)
    elif spec.name == "vwap_reversion":
        vwap_abs_min = _safe_float(params.get("vwap_abs_min"), 0.28)
        buy = (close_to_vwap <= -vwap_abs_min) & (rsi <= 42.0)
        sell = (close_to_vwap >= vwap_abs_min) & (rsi >= 58.0)
    elif spec.name == "rsi_bollinger_reversion":
        buy = (rsi <= _safe_float(params.get("rsi_buy"), 34.0)) & (close <= frame["bb_lower"])
        sell = (rsi >= _safe_float(params.get("rsi_sell"), 66.0)) & (close >= frame["bb_upper"])
    elif spec.name == "atr_breakout_volume":
        volume_floor = _safe_float(params.get("volume_floor"), 1.15)
        buy = (close > (frame["rolling_high_20"] + (0.10 * atr))) & (volume_ratio >= volume_floor)
        sell = (close < (frame["rolling_low_20"] - (0.10 * atr))) & (volume_ratio >= volume_floor)
    elif spec.name == "range_low_vol_reversal":
        mid_vol = pd.to_numeric(frame.get("volatility_mid_flag"), errors="coerce").fillna(0).astype(bool)
        buy = mid_vol & (close_to_vwap <= -0.18) & (rsi <= _safe_float(params.get("rsi_buy"), 40.0))
        sell = mid_vol & (close_to_vwap >= 0.18) & (rsi >= _safe_float(params.get("rsi_sell"), 60.0))
    elif spec.name == "diagnostic_every_trend_tick":
        buy = ema_fast > ema_slow
        sell = ema_fast < ema_slow
    else:
        buy = pd.Series(False, index=frame.index)
        sell = pd.Series(False, index=frame.index)
    out.loc[buy.fillna(False)] = 1
    out.loc[sell.fillna(False)] = 2
    both = buy.fillna(False) & sell.fillna(False)
    out.loc[both] = 0
    return out.astype(int)


def _net_edge_for_signals(frame: pd.DataFrame, signals: pd.Series, *, forward_bars: int, cost_bps: float) -> pd.DataFrame:
    close = pd.to_numeric(frame["close"], errors="coerce").astype(float)
    future_close = close.shift(-int(forward_bars))
    fwd_return_bps = ((future_close / close.replace(0.0, np.nan)) - 1.0) * 10_000.0
    pred = signals.astype(int)
    net_edge = pd.Series(np.nan, index=frame.index, dtype=float)
    net_edge.loc[pred == 1] = fwd_return_bps.loc[pred == 1] - float(cost_bps)
    net_edge.loc[pred == 2] = (-fwd_return_bps.loc[pred == 2]) - float(cost_bps)
    result = frame.copy()
    result["pred"] = pred
    result["forward_return_bps"] = fwd_return_bps
    result["net_edge_bps"] = net_edge
    return result.iloc[:-int(forward_bars)].copy() if forward_bars > 0 else result.copy()


def _profit_factor(edges: np.ndarray) -> float:
    if len(edges) == 0:
        return 0.0
    gains = float(edges[edges > 0.0].sum())
    losses = abs(float(edges[edges < 0.0].sum()))
    if losses <= 0.0:
        return 99.0 if gains > 0.0 else 0.0
    return round(gains / losses, 6)


def evaluate_strategy_edge(
    df: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    spec: StrategyEdgeSpec,
    cost_bps: float = 16.0,
    forward_bars: int | None = None,
    limits: EdgeExplorationLimits | None = None,
) -> dict[str, Any]:
    limits = limits or EdgeExplorationLimits()
    frame = add_edge_features(df)
    fb = int(spec.forward_bars or forward_bars or default_forward_bars(interval))
    signals = _signals_for_strategy(frame, spec)
    sample_frame = _net_edge_for_signals(frame, signals, forward_bars=fb, cost_bps=cost_bps)
    pred = pd.to_numeric(sample_frame.get("pred"), errors="coerce").fillna(0).astype(int).to_numpy(dtype=int)
    all_edges = pd.to_numeric(sample_frame.get("net_edge_bps"), errors="coerce")
    selected_edges = all_edges[np.isin(pred, ACTION_IDS)].dropna().to_numpy(dtype=float)
    signal_count = int(len(selected_edges))
    clean_samples = int(len(sample_frame))
    coverage_pct = _pct(signal_count, clean_samples)
    good_count = int((selected_edges > 0.0).sum()) if signal_count else 0
    win_rate_pct = _pct(good_count, signal_count)
    mean_edge = round(float(np.mean(selected_edges)), 6) if signal_count else 0.0
    median_edge = round(float(np.median(selected_edges)), 6) if signal_count else 0.0
    profit_factor = _profit_factor(selected_edges)
    side_pct = _dominant_action_pct(pred.tolist())
    distribution = _class_distribution(pred.tolist())
    reasons: list[str] = []
    warnings: list[str] = []
    if clean_samples < int(limits.min_clean_samples):
        _append_unique(reasons, "EDGE_SAMPLE_COUNT_LOW")
    if not spec.approvable:
        _append_unique(reasons, "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if signal_count < int(limits.min_signal_count):
        _append_unique(reasons, "EDGE_SIGNAL_COUNT_LOW")
    if coverage_pct < float(limits.min_signal_coverage_pct):
        _append_unique(reasons, "EDGE_COVERAGE_LOW")
    if coverage_pct > float(limits.max_signal_coverage_pct):
        _append_unique(reasons, "EDGE_COVERAGE_HIGH")
    if side_pct > float(limits.max_dominant_action_pct):
        _append_unique(reasons, "EDGE_ACTION_SIDE_IMBALANCE_HIGH")
    if mean_edge < float(limits.min_mean_net_edge_bps):
        _append_unique(reasons, "EDGE_EXPECTED_EDGE_LOW")
    if median_edge < float(limits.min_median_net_edge_bps):
        _append_unique(reasons, "EDGE_MEDIAN_EDGE_LOW")
    if win_rate_pct < float(limits.min_win_rate_pct):
        _append_unique(reasons, "EDGE_WIN_RATE_LOW")
    if profit_factor < float(limits.min_profit_factor):
        _append_unique(reasons, "EDGE_PROFIT_FACTOR_LOW")
    if coverage_pct < float(limits.min_signal_coverage_pct) * 1.5:
        _append_unique(warnings, "EDGE_COVERAGE_NEAR_FLOOR")
    if mean_edge < float(limits.min_mean_net_edge_bps) + 1.0:
        _append_unique(warnings, "EDGE_EXPECTED_EDGE_NEAR_FLOOR")
    # Score prioritizes positive edge, sufficient but not excessive coverage, and balanced sides.
    coverage_penalty = abs(coverage_pct - float(limits.target_signal_coverage_pct)) * 0.35
    side_penalty = max(0.0, side_pct - 55.0) * 0.25
    score = round((mean_edge * 2.0) + (win_rate_pct - 50.0) + (profit_factor * 4.0) - coverage_penalty - side_penalty, 6)
    return {
        "contract_version": TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION,
        "report_type": "strategy_edge_candidate",
        "decision": "PASS" if not reasons else "BLOCK",
        "ok": not reasons,
        "approved_for_research_candidate": not reasons,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "symbol": str(symbol).upper(),
        "interval": str(interval),
        "strategy": spec.to_dict(),
        "cost_bps": float(cost_bps),
        "forward_bars": fb,
        "reason_codes": reasons,
        "warnings": warnings,
        "score": score,
        "metrics": {
            "clean_samples": clean_samples,
            "signal_count": signal_count,
            "signal_coverage_pct": coverage_pct,
            "distribution": distribution,
            "dominant_action_pct": side_pct,
            "mean_net_edge_bps": mean_edge,
            "median_net_edge_bps": median_edge,
            "net_edge_summary": _summary(selected_edges.tolist()),
            "win_rate_pct": win_rate_pct,
            "profit_factor": profit_factor,
            "good_action_count": good_count,
        },
        "limits": limits.to_dict(),
    }


def select_best_edge_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {"decision": "BLOCK", "approved": False, "reason_codes": ["NO_EDGE_CANDIDATES_EVALUATED"], "best_candidate": None}
    ranked = sorted(candidates, key=lambda item: _safe_float(item.get("score"), -999999.0), reverse=True)
    best = ranked[0]
    passed = [item for item in ranked if item.get("decision") == "PASS" and bool(item.get("approved_for_research_candidate"))]
    if passed:
        return {"decision": "PASS", "approved": True, "reason_codes": [], "best_candidate": passed[0]}
    reason_codes: list[str] = ["NO_TIMEFRAME_SYMBOL_STRATEGY_EDGE_PASSED"]
    for item in ranked[:8]:
        for code in item.get("reason_codes") or []:
            _append_unique(reason_codes, str(code))
    return {"decision": "BLOCK", "approved": False, "reason_codes": reason_codes, "best_candidate": best}


def build_timeframe_symbol_strategy_edge_exploration(
    datasets: Mapping[tuple[str, str], pd.DataFrame],
    *,
    strategy_specs: Sequence[StrategyEdgeSpec] | None = None,
    cost_bps: float = 16.0,
    limits: EdgeExplorationLimits | None = None,
    max_combinations: int | None = None,
) -> dict[str, Any]:
    limits = limits or EdgeExplorationLimits()
    specs = list(strategy_specs or default_strategy_specs())
    candidates: list[dict[str, Any]] = []
    evaluated = 0
    for (symbol, interval), df in datasets.items():
        for spec in specs:
            if max_combinations is not None and evaluated >= int(max_combinations):
                break
            candidates.append(evaluate_strategy_edge(df, symbol=symbol, interval=interval, spec=spec, cost_bps=cost_bps, limits=limits))
            evaluated += 1
        if max_combinations is not None and evaluated >= int(max_combinations):
            break
    selection = select_best_edge_candidate(candidates)
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), Mapping) else {}
    best_strategy = best.get("strategy") if isinstance(best.get("strategy"), Mapping) else {}
    decision = str(selection.get("decision", "BLOCK"))
    report = {
        "contract_version": TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION,
        "phase": TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION,
        "report_type": "timeframe_symbol_strategy_edge_exploration",
        "decision": decision,
        "ok": decision == "PASS",
        "candidate_count": len(candidates),
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
        "get_only_public_market_data": True,
        "reason_codes": selection.get("reason_codes") or [],
        "recommendation": (
            "A timeframe/symbol/strategy edge candidate passed the research gate. Use it only for controlled follow-up research; do not train, reload, paper, or live trade yet."
            if decision == "PASS"
            else "No timeframe/symbol/strategy combination showed enough positive net edge. Revisit market, timeframe, feature set, or strategy family before further ML work."
        ),
        "selection": selection,
        "selected_symbol": best.get("symbol"),
        "selected_interval": best.get("interval"),
        "selected_strategy": best_strategy.get("name"),
        "selected_score": best.get("score"),
        "selected_mean_edge_bps": best_metrics.get("mean_net_edge_bps"),
        "selected_win_rate_pct": best_metrics.get("win_rate_pct"),
        "selected_signal_coverage_pct": best_metrics.get("signal_coverage_pct"),
        "candidates": candidates,
        "guardrails": {
            "observation_only": True,
            "get_only_public_market_data": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
        },
    }
    return report
