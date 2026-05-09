from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

HYP003_ROBUSTNESS_CONTRACT_VERSION = "4B.4.3.6.6.25K"
HYP003_ROBUSTNESS_HOTFIX_VERSION = "4B.4.3.6.6.25K-H1"
REPORT_PREFIX = "4B436625K_hyp003_robustness_walkforward_confirmation"
REPORT_TYPE = "hyp003_robustness_walkforward_confirmation_gate"

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


@dataclass(frozen=True)
class Hyp003CandidateSpec:
    hypothesis_id: str = "HYP-003"
    symbol: str = "ETHUSDT"
    interval: str = "4h"
    strategy: str = "range_mean_reversion"
    regime: str = "range"
    source_phase: str = "4B.4.3.6.6.25J"
    hold_bars: int = 1
    round_trip_cost_bps: float = 16.0
    min_edge_bps: float = 0.0


@dataclass(frozen=True)
class Hyp003RobustnessLimits:
    min_signal_count: int = 40
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.20
    min_win_rate_pct: float = 48.0
    min_walk_forward_positive_rate_pct: float = 60.0
    min_oos_mean_net_edge_bps: float = 0.0
    max_top_win_dependency_pct: float = 45.0
    max_dominant_side_pct: float = 78.0
    min_regime_signal_pct: float = 80.0
    min_recent_window_signal_count: int = 10
    max_recent_window_count: int = 3
    max_drawdown_pct: float = 30.0


@dataclass(frozen=True)
class SignalMetrics:
    signal_count: int
    mean_net_edge_bps: float
    median_net_edge_bps: float
    profit_factor: float
    win_rate_pct: float
    gross_win_bps: float
    gross_loss_bps: float
    top_win_dependency_pct: float
    dominant_side_pct: float
    max_drawdown_pct: float
    side_counts: dict[str, int]


@dataclass(frozen=True)
class RobustnessSegment:
    name: str
    signal_count: int
    mean_net_edge_bps: float
    median_net_edge_bps: float
    profit_factor: float
    win_rate_pct: float
    decision: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class RobustnessCandidateResult:
    contract_version: str
    candidate_spec: dict[str, Any]
    decision: str
    ok: bool
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    reload_allowed: bool
    signal_metrics: dict[str, Any]
    walk_forward_segments: list[dict[str, Any]]
    recent_window_segments: list[dict[str, Any]]
    oos_segment: dict[str, Any]
    regime_metrics: dict[str, Any]
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        return out if isfinite(out) else default
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(default)
    return pd.Series(default, index=frame.index, dtype="float64")


def normalize_market_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    aliases = {
        "openTime": "timestamp",
        "open_time": "timestamp",
        "time": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = out.rename(columns={key: value for key, value in aliases.items() if key in out.columns})
    for column in ["open", "high", "low", "close"]:
        if column not in out.columns:
            raise ValueError(f"missing OHLC column: {column}")
        out[column] = pd.to_numeric(out[column], errors="coerce")
    if "volume" not in out.columns:
        out["volume"] = 0.0
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)
    if "timestamp" in out.columns:
        ts = out["timestamp"]
        if pd.api.types.is_numeric_dtype(ts):
            max_ts = float(pd.to_numeric(ts, errors="coerce").max())
            unit = "ms" if max_ts > 10_000_000_000 else "s"
            out["timestamp"] = pd.to_datetime(ts, unit=unit, utc=True, errors="coerce")
        else:
            out["timestamp"] = pd.to_datetime(ts, utc=True, errors="coerce")
        out = out.sort_values("timestamp")
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return out


def add_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_market_dataframe(df)
    if out.empty:
        return out
    close = _series(out, "close")
    high = _series(out, "high")
    low = _series(out, "low")
    volume = _series(out, "volume")
    out["ema_fast"] = close.ewm(span=21, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=55, adjust=False).mean()
    out["ema_gap_pct"] = (out["ema_fast"] / out["ema_slow"].replace(0, np.nan) - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    mid = close.rolling(20, min_periods=5).mean()
    std = close.rolling(20, min_periods=5).std(ddof=0)
    out["bb_mid"] = mid.fillna(close)
    out["bb_upper"] = (mid + 2.0 * std).fillna(close)
    out["bb_lower"] = (mid - 2.0 * std).fillna(close)
    out["bb_width_pct"] = ((out["bb_upper"] - out["bb_lower"]) / out["bb_mid"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    tr = pd.concat([(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    out["atr"] = tr.rolling(14, min_periods=3).mean().fillna(tr.expanding(min_periods=1).mean())
    out["atr_pct"] = (out["atr"] / close.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=3).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=3).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = (100 - (100 / (1 + rs))).fillna(50.0)
    out["volume_ratio"] = (volume / volume.rolling(30, min_periods=5).mean().replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    range_score = (out["ema_gap_pct"].abs() < 0.004) & (out["atr_pct"] < out["atr_pct"].rolling(100, min_periods=20).quantile(0.75).fillna(out["atr_pct"].median()))
    high_vol = out["atr_pct"] >= out["atr_pct"].rolling(100, min_periods=20).quantile(0.75).fillna(out["atr_pct"].median())
    trend = out["ema_gap_pct"].abs() >= 0.004
    out["regime"] = np.where(range_score, "range", np.where(high_vol & trend, "high_vol_trend", np.where(trend, "trend", "low_vol")))
    return out


def parse_hyp003_candidate_from_25j(report: Mapping[str, Any]) -> Hyp003CandidateSpec:
    selected = report.get("selected") if isinstance(report.get("selected"), Mapping) else {}
    candidate = report.get("selected_candidate") if isinstance(report.get("selected_candidate"), Mapping) else {}
    spec = report.get("candidate_spec") if isinstance(report.get("candidate_spec"), Mapping) else {}
    raw = {**spec, **candidate, **selected}
    selected_text = str(report.get("selected") or "") if not isinstance(report.get("selected"), Mapping) else ""
    parts = selected_text.split()
    symbol = str(raw.get("symbol") or report.get("selected_symbol") or (parts[0] if len(parts) >= 4 else "ETHUSDT")).upper()
    interval = str(raw.get("interval") or report.get("selected_interval") or (parts[1] if len(parts) >= 4 else "4h"))
    strategy = str(raw.get("strategy") or report.get("selected_strategy") or (parts[2] if len(parts) >= 4 else "range_mean_reversion"))
    regime = str(raw.get("regime") or report.get("selected_regime") or (parts[3] if len(parts) >= 4 else "range"))
    hypothesis_id = str(report.get("hypothesis_id") or raw.get("hypothesis_id") or "HYP-003")
    return Hyp003CandidateSpec(
        hypothesis_id=hypothesis_id,
        symbol=symbol,
        interval=interval,
        strategy=strategy,
        regime=regime,
        source_phase=str(report.get("contract_version") or report.get("phase") or "4B.4.3.6.6.25J"),
    )


def generate_candidate_signals(features: pd.DataFrame, spec: Hyp003CandidateSpec) -> pd.DataFrame:
    out = add_regime_features(features)
    if out.empty:
        return out.assign(signal=False, side=HOLD, signal_reason="NO_DATA")
    close = _series(out, "close")
    rsi = _series(out, "rsi", 50.0)
    if spec.strategy == "range_mean_reversion":
        in_regime = out["regime"].astype(str).eq(spec.regime)
        band_std = ((out["bb_upper"] - out["bb_mid"]) / 2.0).replace(0, np.nan).fillna(0.0)
        lower_trigger = out["bb_mid"] - 0.85 * band_std
        upper_trigger = out["bb_mid"] + 0.85 * band_std
        buy = in_regime & (close <= lower_trigger) & (rsi <= 52)
        sell = in_regime & (close >= upper_trigger) & (rsi >= 48)
    elif spec.strategy == "volatility_expansion_breakout":
        in_regime = out["regime"].astype(str).isin([spec.regime, "high_vol_trend"])
        prior_high = _series(out, "high").rolling(20, min_periods=5).max().shift(1)
        prior_low = _series(out, "low").rolling(20, min_periods=5).min().shift(1)
        buy = in_regime & (close > prior_high)
        sell = in_regime & (close < prior_low)
    elif spec.strategy == "trend_pullback_continuation":
        in_regime = out["regime"].astype(str).isin([spec.regime, "trend", "high_vol_trend"])
        buy = in_regime & (_series(out, "ema_gap_pct") > 0) & (rsi < 48)
        sell = in_regime & (_series(out, "ema_gap_pct") < 0) & (rsi > 52)
    else:
        in_regime = out["regime"].astype(str).eq(spec.regime)
        buy = pd.Series(False, index=out.index)
        sell = pd.Series(False, index=out.index)
    side = np.where(buy, BUY, np.where(sell, SELL, HOLD))
    out["signal"] = buy | sell
    out["side"] = side
    out["signal_reason"] = np.where(out["signal"], f"{spec.strategy}:{spec.regime}", "HOLD")
    return out


def _profit_factor(edges: Sequence[float]) -> float:
    arr = np.asarray(edges, dtype="float64")
    wins = float(arr[arr > 0].sum())
    losses = float(abs(arr[arr < 0].sum()))
    if wins <= 0 and losses <= 0:
        return 0.0
    if losses == 0:
        return 99.0
    return wins / losses


def _max_drawdown_pct(edges: Sequence[float]) -> float:
    if not edges:
        return 0.0
    equity = np.cumsum(np.asarray(edges, dtype="float64")) / 10000.0
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    return float(np.max(drawdown) * 100.0) if len(drawdown) else 0.0


def _top_win_dependency_pct(edges: Sequence[float], top_n: int = 3) -> float:
    arr = np.asarray(edges, dtype="float64")
    wins = np.sort(arr[arr > 0])[::-1]
    total = float(wins.sum())
    if total <= 0:
        return 100.0
    return 100.0 * float(wins[:top_n].sum()) / total


def _dominant_side_pct(sides: Sequence[str]) -> float:
    sides = [side for side in sides if side in {BUY, SELL}]
    if not sides:
        return 0.0
    buy = sum(side == BUY for side in sides)
    sell = sum(side == SELL for side in sides)
    return 100.0 * max(buy, sell) / len(sides)


def _edge_rows(signals: pd.DataFrame, spec: Hyp003CandidateSpec) -> pd.DataFrame:
    if signals.empty:
        return pd.DataFrame()
    horizon = max(1, int(spec.hold_bars))
    rows = signals[signals["signal"].astype(bool)].copy()
    rows = rows[rows.index < len(signals) - horizon].copy()
    if rows.empty:
        return rows.assign(net_edge_bps=[], gross_edge_bps=[])
    close = _series(signals, "close")
    entry = close.loc[rows.index].to_numpy(dtype="float64")
    exit_ = close.shift(-horizon).loc[rows.index].to_numpy(dtype="float64")
    side_sign = np.asarray([1.0 if side == BUY else -1.0 if side == SELL else 0.0 for side in rows["side"]], dtype="float64")
    gross = side_sign * ((exit_ / entry) - 1.0) * 10000.0
    gross = np.nan_to_num(gross, nan=0.0, posinf=0.0, neginf=0.0)
    rows["gross_edge_bps"] = gross
    rows["net_edge_bps"] = gross - float(spec.round_trip_cost_bps) - float(spec.min_edge_bps)
    return rows


def _ensure_edges_dataframe(edges: Any) -> pd.DataFrame:
    """Return a DataFrame for edge summaries even if a splitter returns ndarray.

    25K-H1 fixes Python/numpy environments where ``np.array_split`` on a
    DataFrame yields ndarray chunks, which broke ``summarize_edges`` with
    ``AttributeError: numpy.ndarray object has no attribute empty``.
    """
    if isinstance(edges, pd.DataFrame):
        return edges
    if isinstance(edges, pd.Series):
        return edges.to_frame().T
    return pd.DataFrame(edges)


def _split_dataframe(frame: pd.DataFrame, windows: int) -> list[pd.DataFrame]:
    if frame.empty:
        return []
    actual_windows = max(1, min(int(windows), len(frame)))
    index_chunks = np.array_split(np.arange(len(frame)), actual_windows)
    return [frame.iloc[chunk].copy() for chunk in index_chunks if len(chunk)]


def summarize_edges(edges: pd.DataFrame) -> SignalMetrics:
    edges = _ensure_edges_dataframe(edges)
    if edges.empty:
        return SignalMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, {BUY: 0, SELL: 0})
    net = edges["net_edge_bps"].to_numpy(dtype="float64")
    sides = list(edges.get("side", pd.Series(dtype="object")))
    side_counts = {BUY: int(sum(side == BUY for side in sides)), SELL: int(sum(side == SELL for side in sides))}
    wins = float(net[net > 0].sum())
    losses = float(abs(net[net < 0].sum()))
    return SignalMetrics(
        signal_count=int(len(net)),
        mean_net_edge_bps=round(float(np.mean(net)), 6),
        median_net_edge_bps=round(float(np.median(net)), 6),
        profit_factor=round(_profit_factor(net), 6),
        win_rate_pct=round(float(np.mean(net > 0)) * 100.0, 6),
        gross_win_bps=round(wins, 6),
        gross_loss_bps=round(losses, 6),
        top_win_dependency_pct=round(_top_win_dependency_pct(net), 6),
        dominant_side_pct=round(_dominant_side_pct(sides), 6),
        max_drawdown_pct=round(_max_drawdown_pct(list(net)), 6),
        side_counts=side_counts,
    )


def evaluate_segment(edges: pd.DataFrame, name: str, limits: Hyp003RobustnessLimits, *, allow_low_count: bool = False) -> RobustnessSegment:
    edges = _ensure_edges_dataframe(edges)
    metrics = summarize_edges(edges)
    reasons: list[str] = []
    if not allow_low_count and metrics.signal_count < limits.min_recent_window_signal_count:
        reasons.append("SEGMENT_SIGNAL_COUNT_LOW")
    if metrics.mean_net_edge_bps <= limits.min_mean_net_edge_bps:
        reasons.append("SEGMENT_MEAN_EDGE_LOW")
    if metrics.median_net_edge_bps <= limits.min_median_net_edge_bps:
        reasons.append("SEGMENT_MEDIAN_EDGE_LOW")
    if metrics.profit_factor < limits.min_profit_factor:
        reasons.append("SEGMENT_PROFIT_FACTOR_LOW")
    decision = "PASS" if not reasons else "BLOCK"
    return RobustnessSegment(
        name=name,
        signal_count=metrics.signal_count,
        mean_net_edge_bps=metrics.mean_net_edge_bps,
        median_net_edge_bps=metrics.median_net_edge_bps,
        profit_factor=metrics.profit_factor,
        win_rate_pct=metrics.win_rate_pct,
        decision=decision,
        reason_codes=tuple(reasons),
    )


def split_walk_forward(edges: pd.DataFrame, limits: Hyp003RobustnessLimits, windows: int = 4) -> list[RobustnessSegment]:
    edges = _ensure_edges_dataframe(edges)
    if edges.empty:
        return [evaluate_segment(edges, f"wf_{idx+1}", limits) for idx in range(windows)]
    ordered = edges.sort_values("timestamp") if "timestamp" in edges.columns else edges.copy()
    chunks = _split_dataframe(ordered, windows)
    return [evaluate_segment(chunk, f"wf_{idx+1}", limits, allow_low_count=True) for idx, chunk in enumerate(chunks)]


def recent_window_segments(edges: pd.DataFrame, limits: Hyp003RobustnessLimits, window_count: int | None = None) -> list[RobustnessSegment]:
    window_count = window_count or limits.max_recent_window_count
    edges = _ensure_edges_dataframe(edges)
    if edges.empty:
        return [evaluate_segment(edges, f"recent_{idx+1}", limits) for idx in range(window_count)]
    ordered = edges.sort_values("timestamp") if "timestamp" in edges.columns else edges.copy()
    chunks = _split_dataframe(ordered, window_count)
    chunks = chunks[-window_count:]
    return [evaluate_segment(chunk, f"recent_{idx+1}", limits, allow_low_count=True) for idx, chunk in enumerate(chunks)]


def build_hyp003_robustness_walkforward_report(
    market_df: pd.DataFrame,
    candidate_spec: Hyp003CandidateSpec | None = None,
    limits: Hyp003RobustnessLimits | None = None,
    source: str = "dataframe",
) -> dict[str, Any]:
    spec = candidate_spec or Hyp003CandidateSpec()
    limits = limits or Hyp003RobustnessLimits()
    signals = generate_candidate_signals(market_df, spec)
    edges = _edge_rows(signals, spec)
    metrics = summarize_edges(edges)
    wf = split_walk_forward(edges, limits)
    recent = recent_window_segments(edges, limits)
    oos_cut = int(len(edges) * 0.70) if len(edges) else 0
    oos_edges = edges.iloc[oos_cut:].copy() if len(edges) else edges
    oos = evaluate_segment(oos_edges, "oos_last_30pct", limits, allow_low_count=True)
    positive_wf = sum(seg.mean_net_edge_bps > 0 for seg in wf)
    wf_positive_rate = 100.0 * positive_wf / max(1, len(wf))
    regime_signal_pct = 0.0
    if not signals.empty and "signal" in signals.columns:
        total_signals = int(signals["signal"].sum())
        if total_signals:
            regime_signal_pct = 100.0 * int((signals["signal"] & signals["regime"].astype(str).eq(spec.regime)).sum()) / total_signals
    reason_codes: list[str] = []
    warnings: list[str] = []
    if metrics.signal_count < limits.min_signal_count:
        reason_codes.append("ROBUST_SIGNAL_COUNT_LOW")
    if metrics.mean_net_edge_bps <= limits.min_mean_net_edge_bps:
        reason_codes.append("ROBUST_MEAN_EDGE_LOW")
    if metrics.median_net_edge_bps <= limits.min_median_net_edge_bps:
        reason_codes.append("ROBUST_MEDIAN_EDGE_LOW")
    if metrics.profit_factor < limits.min_profit_factor:
        reason_codes.append("ROBUST_PROFIT_FACTOR_LOW")
    if metrics.win_rate_pct < limits.min_win_rate_pct:
        reason_codes.append("ROBUST_WIN_RATE_LOW")
    if wf_positive_rate < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("ROBUST_WALK_FORWARD_STABILITY_LOW")
    if oos.mean_net_edge_bps <= limits.min_oos_mean_net_edge_bps:
        reason_codes.append("ROBUST_OOS_EDGE_LOW")
    if metrics.top_win_dependency_pct > limits.max_top_win_dependency_pct:
        reason_codes.append("ROBUST_TOP_WIN_DEPENDENCY_HIGH")
    if metrics.dominant_side_pct > limits.max_dominant_side_pct:
        reason_codes.append("ROBUST_SIDE_IMBALANCE_HIGH")
    if regime_signal_pct < limits.min_regime_signal_pct:
        reason_codes.append("ROBUST_REGIME_PERSISTENCE_LOW")
    if metrics.max_drawdown_pct > limits.max_drawdown_pct:
        reason_codes.append("ROBUST_MAX_DRAWDOWN_HIGH")
    if metrics.signal_count < limits.min_signal_count + 10:
        warnings.append("ROBUST_SIGNAL_COUNT_NEAR_FLOOR")
    if metrics.mean_net_edge_bps > 0 and metrics.median_net_edge_bps <= 0:
        warnings.append("MEAN_POSITIVE_BUT_MEDIAN_NON_POSITIVE")
    decision = "HYP003_ROBUSTNESS_PASS" if not reason_codes else "HYP003_ROBUSTNESS_BLOCK"
    recommendation = (
        "HYP-003 candidate passed robustness/walk-forward confirmation as research-only. Do not train, reload, paper trade, or enable live trading; move to candidate specification and no-order shadow planning gate."
        if decision == "HYP003_ROBUSTNESS_PASS"
        else "HYP-003 candidate failed robustness/walk-forward confirmation. Do not train, reload, paper trade, or enable live trading; refine or close this candidate."
    )
    return {
        "contract_version": HYP003_ROBUSTNESS_CONTRACT_VERSION,
        "phase": HYP003_ROBUSTNESS_CONTRACT_VERSION,
        "report_type": REPORT_TYPE,
        "decision": decision,
        "ok": decision == "HYP003_ROBUSTNESS_PASS",
        "source": source,
        "candidate_spec": asdict(spec),
        "limits": asdict(limits),
        "signal_metrics": asdict(metrics),
        "walk_forward_segments": [asdict(seg) for seg in wf],
        "walk_forward_positive_rate_pct": round(wf_positive_rate, 6),
        "recent_window_segments": [asdict(seg) for seg in recent],
        "oos_segment": asdict(oos),
        "regime_metrics": {
            "target_regime": spec.regime,
            "regime_signal_pct": round(regime_signal_pct, 6),
            "total_bars": int(len(signals)),
            "signal_bars": int(signals["signal"].sum()) if not signals.empty and "signal" in signals.columns else 0,
        },
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
        "recommendation": recommendation,
        "approved_for_research_candidate": decision == "HYP003_ROBUSTNESS_PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
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
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    metrics = report.get("signal_metrics", {}) if isinstance(report.get("signal_metrics"), Mapping) else {}
    spec = report.get("candidate_spec", {}) if isinstance(report.get("candidate_spec"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25K HYP-003 Robustness / Walk-Forward Confirmation Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{spec.get('hypothesis_id')}`",
        f"- selected: `{spec.get('symbol')} {spec.get('interval')} {spec.get('strategy')} {spec.get('regime')}`",
        f"- signal_count: `{metrics.get('signal_count')}`",
        f"- mean_net_edge_bps: `{metrics.get('mean_net_edge_bps')}`",
        f"- median_net_edge_bps: `{metrics.get('median_net_edge_bps')}`",
        f"- profit_factor: `{metrics.get('profit_factor')}`",
        f"- win_rate_pct: `{metrics.get('win_rate_pct')}`",
        f"- walk_forward_positive_rate_pct: `{report.get('walk_forward_positive_rate_pct')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Walk-Forward Segments",
        "",
        "| segment | decision | signals | mean_edge_bps | median_edge_bps | profit_factor | win_rate_pct | reasons |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for seg in report.get("walk_forward_segments", []):
        lines.append(
            f"| {seg.get('name')} | {seg.get('decision')} | {seg.get('signal_count')} | {seg.get('mean_net_edge_bps')} | {seg.get('median_net_edge_bps')} | {seg.get('profit_factor')} | {seg.get('win_rate_pct')} | `{seg.get('reason_codes')}` |"
        )
    lines.extend([
        "",
        "## OOS Segment",
        "",
        f"- decision: `{report.get('oos_segment', {}).get('decision') if isinstance(report.get('oos_segment'), Mapping) else None}`",
        f"- mean_net_edge_bps: `{report.get('oos_segment', {}).get('mean_net_edge_bps') if isinstance(report.get('oos_segment'), Mapping) else None}`",
        f"- median_net_edge_bps: `{report.get('oos_segment', {}).get('median_net_edge_bps') if isinstance(report.get('oos_segment'), Mapping) else None}`",
        "",
        "## Guardrails",
        "",
    ])
    for key, value in dict(report.get("guardrails", {})).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Policy",
        "",
        "This gate never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. PASS is research-only.",
    ])
    return "\n".join(lines) + "\n"
