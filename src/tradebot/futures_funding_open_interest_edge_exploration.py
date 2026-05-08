from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION = "4B.4.3.6.6.25B"
REPORT_PREFIX = "4B436625B_futures_funding_open_interest_edge_exploration"

BUY = 1
SELL = -1
HOLD = 0


@dataclass(frozen=True)
class FuturesEdgeSpec:
    name: str
    family: str
    forward_bars: int = 3
    cost_bps: float = 18.0
    min_edge_bps: float = 3.0
    approvable: bool = True
    funding_z: float = 1.0
    long_short_z: float = 0.7
    oi_change_pct: float = 0.15
    taker_ratio: float = 1.04
    trend_gap_pct: float = 0.10
    rsi_high: float = 64.0
    rsi_low: float = 36.0
    volume_ratio: float = 1.10


@dataclass(frozen=True)
class FuturesEdgeLimits:
    min_clean_samples: int = 300
    min_signal_count: int = 20
    min_signal_coverage_pct: float = 0.15
    max_signal_coverage_pct: float = 28.0
    max_dominant_action_pct: float = 82.0
    min_mean_net_edge_bps: float = 1.0
    min_median_net_edge_bps: float = 0.0
    min_win_rate_pct: float = 48.0
    min_profit_factor: float = 1.15
    max_drawdown_pct: float = 35.0
    min_oos_mean_net_edge_bps: float = 0.5
    min_walk_forward_positive_rate_pct: float = 50.0
    min_metric_coverage_pct: float = 20.0


@dataclass
class FuturesEdgeEvaluation:
    contract_version: str
    decision: str
    ok: bool
    symbol: str
    interval: str
    strategy: str
    family: str
    approvable: bool
    score: float
    clean_samples: int
    signal_count: int
    signal_coverage_pct: float
    buy_count: int
    sell_count: int
    dominant_action_pct: float
    mean_net_edge_bps: float
    median_net_edge_bps: float
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    oos_mean_net_edge_bps: float
    walk_forward_positive_rate_pct: float
    metric_coverage: dict[str, float]
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def default_futures_edge_specs() -> list[FuturesEdgeSpec]:
    return [
        FuturesEdgeSpec(
            name="funding_crowding_reversal",
            family="funding_contrarian",
            forward_bars=3,
            cost_bps=18.0,
            funding_z=1.0,
            long_short_z=0.7,
            min_edge_bps=3.0,
        ),
        FuturesEdgeSpec(
            name="oi_taker_trend_confirmation",
            family="flow_trend",
            forward_bars=3,
            cost_bps=18.0,
            oi_change_pct=0.15,
            taker_ratio=1.04,
            trend_gap_pct=0.08,
            min_edge_bps=3.0,
        ),
        FuturesEdgeSpec(
            name="funding_trend_exhaustion",
            family="crowded_trend_reversal",
            forward_bars=4,
            cost_bps=18.0,
            funding_z=1.2,
            trend_gap_pct=0.12,
            rsi_high=64.0,
            rsi_low=36.0,
            min_edge_bps=3.0,
        ),
        FuturesEdgeSpec(
            name="long_short_ratio_reversion",
            family="positioning_reversion",
            forward_bars=3,
            cost_bps=18.0,
            long_short_z=1.0,
            rsi_high=62.0,
            rsi_low=38.0,
            min_edge_bps=3.0,
        ),
        FuturesEdgeSpec(
            name="oi_breakout_taker_volume",
            family="flow_breakout",
            forward_bars=3,
            cost_bps=18.0,
            oi_change_pct=0.20,
            taker_ratio=1.06,
            volume_ratio=1.15,
            min_edge_bps=3.0,
        ),
        FuturesEdgeSpec(
            name="diagnostic_taker_flow_tick",
            family="diagnostic",
            forward_bars=2,
            cost_bps=18.0,
            taker_ratio=1.0,
            min_edge_bps=3.0,
            approvable=False,
        ),
    ]


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _series_float(df: pd.DataFrame, column: str, default: float = np.nan) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def _normalize_timestamp_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "open_time" in out.columns:
        ts = out["open_time"]
    elif "timestamp" in out.columns:
        ts = out["timestamp"]
    elif "time" in out.columns:
        ts = out["time"]
    elif "date" in out.columns:
        ts = out["date"]
    else:
        out["timestamp"] = pd.RangeIndex(start=0, stop=len(out), step=1)
        return out

    if pd.api.types.is_numeric_dtype(ts):
        numeric = pd.to_numeric(ts, errors="coerce")
        if numeric.dropna().median() > 10_000_000_000:
            out["timestamp"] = pd.to_datetime(numeric, unit="ms", utc=True)
        else:
            out["timestamp"] = pd.to_datetime(numeric, unit="s", utc=True)
    else:
        out["timestamp"] = pd.to_datetime(ts, utc=True, errors="coerce")
    return out


def normalize_ohlcv_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_timestamp_column(df)
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "fundingRate": "funding_rate",
        "sumOpenInterest": "sum_open_interest",
        "sumOpenInterestValue": "sum_open_interest_value",
        "longShortRatio": "long_short_ratio",
        "buySellRatio": "taker_buy_sell_ratio",
        "buyVol": "taker_buy_volume",
        "sellVol": "taker_sell_volume",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})
    required = ["open", "high", "low", "close", "volume"]
    for column in required:
        if column not in out.columns:
            raise ValueError(f"Missing required OHLCV column: {column}")
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=required).reset_index(drop=True)
    return out


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0.0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0.0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def _rolling_z(series: pd.Series, window: int = 96) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    mean = values.rolling(window, min_periods=max(8, window // 8)).mean()
    std = values.rolling(window, min_periods=max(8, window // 8)).std(ddof=0)
    return ((values - mean) / std.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def add_futures_behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_ohlcv_frame(df)
    close = out["close"]
    high = out["high"]
    low = out["low"]

    out["ema_21"] = close.ewm(span=21, adjust=False).mean()
    out["ema_55"] = close.ewm(span=55, adjust=False).mean()
    out["ema_gap_pct"] = (out["ema_21"] - out["ema_55"]) / close.replace(0.0, np.nan) * 100.0
    true_range = pd.concat(
        [(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    out["atr_14"] = true_range.rolling(14, min_periods=3).mean().fillna(true_range.expanding().mean())
    out["atr_pct"] = out["atr_14"] / close.replace(0.0, np.nan) * 100.0
    out["rsi_14"] = _rsi(close)
    out["volume_sma_48"] = out["volume"].rolling(48, min_periods=8).mean()
    out["volume_ratio"] = out["volume"] / out["volume_sma_48"].replace(0.0, np.nan)
    out["range_pct"] = (high - low) / close.replace(0.0, np.nan) * 100.0

    out["funding_rate"] = _series_float(out, "funding_rate", 0.0).ffill().fillna(0.0)
    out["funding_rate_bps"] = out["funding_rate"] * 10_000.0
    out["funding_z"] = _rolling_z(out["funding_rate_bps"], 96)

    out["sum_open_interest"] = _series_float(out, "sum_open_interest", np.nan).ffill()
    out["oi_change_pct"] = out["sum_open_interest"].pct_change(3).replace([np.inf, -np.inf], np.nan) * 100.0
    out["oi_change_pct"] = out["oi_change_pct"].fillna(0.0)

    out["long_short_ratio"] = _series_float(out, "long_short_ratio", np.nan).ffill()
    out["long_short_z"] = _rolling_z(out["long_short_ratio"], 96)

    out["taker_buy_sell_ratio"] = _series_float(out, "taker_buy_sell_ratio", np.nan).ffill()
    if "taker_buy_volume" in out.columns and "taker_sell_volume" in out.columns:
        buy = _series_float(out, "taker_buy_volume", np.nan)
        sell = _series_float(out, "taker_sell_volume", np.nan)
        ratio = buy / sell.replace(0.0, np.nan)
        out["taker_buy_sell_ratio"] = out["taker_buy_sell_ratio"].fillna(ratio)
    out["taker_buy_sell_ratio"] = out["taker_buy_sell_ratio"].fillna(1.0)
    out["taker_ratio_z"] = _rolling_z(out["taker_buy_sell_ratio"], 96)

    out = out.replace([np.inf, -np.inf], np.nan)
    return out.dropna(subset=["close", "ema_21", "ema_55"]).reset_index(drop=True)


def metric_coverage(df: pd.DataFrame) -> dict[str, float]:
    cover: dict[str, float] = {}
    metrics = ["funding_rate", "sum_open_interest", "long_short_ratio", "taker_buy_sell_ratio"]
    total = max(1, len(df))
    for column in metrics:
        if column not in df.columns:
            cover[column] = 0.0
            continue
        cover[column] = round(float(pd.to_numeric(df[column], errors="coerce").notna().sum() / total * 100.0), 6)
    return cover


def build_strategy_signal(df: pd.DataFrame, spec: FuturesEdgeSpec) -> pd.Series:
    signal = pd.Series(HOLD, index=df.index, dtype="int64")
    trend_up = df["ema_gap_pct"] > spec.trend_gap_pct
    trend_down = df["ema_gap_pct"] < -spec.trend_gap_pct
    volume_ok = df["volume_ratio"].fillna(0.0) >= spec.volume_ratio
    oi_ok = df["oi_change_pct"].fillna(0.0) >= spec.oi_change_pct
    taker_buy = df["taker_buy_sell_ratio"].fillna(1.0) >= spec.taker_ratio
    taker_sell = df["taker_buy_sell_ratio"].fillna(1.0) <= (1.0 / max(spec.taker_ratio, 1.000001))

    if spec.name == "funding_crowding_reversal":
        signal[(df["funding_z"] <= -spec.funding_z) & (df["long_short_z"] <= -spec.long_short_z)] = BUY
        signal[(df["funding_z"] >= spec.funding_z) & (df["long_short_z"] >= spec.long_short_z)] = SELL
    elif spec.name == "oi_taker_trend_confirmation":
        signal[trend_up & oi_ok & taker_buy] = BUY
        signal[trend_down & oi_ok & taker_sell] = SELL
    elif spec.name == "funding_trend_exhaustion":
        signal[trend_up & (df["funding_z"] >= spec.funding_z) & (df["rsi_14"] >= spec.rsi_high)] = SELL
        signal[trend_down & (df["funding_z"] <= -spec.funding_z) & (df["rsi_14"] <= spec.rsi_low)] = BUY
    elif spec.name == "long_short_ratio_reversion":
        signal[(df["long_short_z"] >= spec.long_short_z) & (df["rsi_14"] >= spec.rsi_high)] = SELL
        signal[(df["long_short_z"] <= -spec.long_short_z) & (df["rsi_14"] <= spec.rsi_low)] = BUY
    elif spec.name == "oi_breakout_taker_volume":
        rolling_high = df["high"].rolling(24, min_periods=8).max().shift(1)
        rolling_low = df["low"].rolling(24, min_periods=8).min().shift(1)
        signal[(df["close"] > rolling_high) & oi_ok & volume_ok & taker_buy] = BUY
        signal[(df["close"] < rolling_low) & oi_ok & volume_ok & taker_sell] = SELL
    elif spec.name == "diagnostic_taker_flow_tick":
        signal[df["taker_buy_sell_ratio"] > spec.taker_ratio] = BUY
        signal[df["taker_buy_sell_ratio"] < 1.0 / max(spec.taker_ratio, 1.000001)] = SELL
    else:
        raise ValueError(f"Unsupported futures strategy: {spec.name}")
    return signal


def net_edge_for_signals(df: pd.DataFrame, signal: pd.Series, spec: FuturesEdgeSpec) -> pd.Series:
    future_close = df["close"].shift(-spec.forward_bars)
    current_close = df["close"]
    long_edge = (future_close - current_close) / current_close.replace(0.0, np.nan) * 10_000.0
    short_edge = (current_close - future_close) / current_close.replace(0.0, np.nan) * 10_000.0
    raw_edge = pd.Series(np.nan, index=df.index, dtype="float64")
    raw_edge[signal == BUY] = long_edge[signal == BUY]
    raw_edge[signal == SELL] = short_edge[signal == SELL]
    return raw_edge - spec.cost_bps


def _profit_factor(edges: pd.Series) -> float:
    gains = float(edges[edges > 0.0].sum())
    losses = float(edges[edges < 0.0].sum())
    if losses == 0.0:
        return 999.0 if gains > 0.0 else 0.0
    return gains / abs(losses)


def _max_drawdown_pct(edges: pd.Series) -> float:
    if edges.empty:
        return 0.0
    equity_bps = edges.fillna(0.0).cumsum()
    drawdown_bps = equity_bps.cummax() - equity_bps
    return round(float(drawdown_bps.max() / 100.0), 6)


def _walk_forward_positive_rate(edges: pd.Series, folds: int = 4) -> float:
    clean = edges.dropna().reset_index(drop=True)
    if clean.empty:
        return 0.0
    chunks = np.array_split(clean, min(folds, len(clean)))
    positive = sum(float(chunk.mean()) > 0.0 for chunk in chunks if len(chunk) > 0)
    return round(float(positive / max(1, len(chunks)) * 100.0), 6)


def evaluate_futures_strategy_edge(
    df: pd.DataFrame,
    spec: FuturesEdgeSpec,
    *,
    symbol: str,
    interval: str,
    limits: FuturesEdgeLimits | None = None,
) -> FuturesEdgeEvaluation:
    limits = limits or FuturesEdgeLimits()
    features = add_futures_behavior_features(df)
    clean_samples = int(len(features))
    signal = build_strategy_signal(features, spec)
    edges = net_edge_for_signals(features, signal, spec).dropna()
    signal_mask = signal.loc[edges.index] != HOLD if not edges.empty else pd.Series(False, index=features.index)
    signal_edges = edges[signal_mask]
    signal_count = int(len(signal_edges))
    signal_coverage_pct = round(float(signal_count / max(1, clean_samples) * 100.0), 6)
    buy_count = int((signal == BUY).sum())
    sell_count = int((signal == SELL).sum())
    action_total = max(1, buy_count + sell_count)
    dominant_action_pct = round(float(max(buy_count, sell_count) / action_total * 100.0), 6) if signal_count else 0.0

    mean_edge = round(float(signal_edges.mean()), 6) if signal_count else 0.0
    median_edge = round(float(signal_edges.median()), 6) if signal_count else 0.0
    win_rate = round(float((signal_edges > 0.0).mean() * 100.0), 6) if signal_count else 0.0
    pf = round(float(_profit_factor(signal_edges)), 6) if signal_count else 0.0
    max_dd = _max_drawdown_pct(signal_edges)
    if signal_count >= 3:
        split = max(1, int(signal_count * 0.7))
        oos_edge = round(float(signal_edges.reset_index(drop=True).iloc[split:].mean()), 6)
        if math.isnan(oos_edge):
            oos_edge = 0.0
    else:
        oos_edge = 0.0
    wf_positive = _walk_forward_positive_rate(signal_edges)
    coverage = metric_coverage(features)

    reasons: list[str] = []
    warnings: list[str] = []
    if clean_samples < limits.min_clean_samples:
        reasons.append("EDGE_SAMPLE_COUNT_LOW")
    if signal_count < limits.min_signal_count:
        reasons.append("EDGE_SIGNAL_COUNT_LOW")
    if signal_coverage_pct < limits.min_signal_coverage_pct:
        reasons.append("EDGE_COVERAGE_LOW")
    if signal_coverage_pct > limits.max_signal_coverage_pct:
        reasons.append("EDGE_COVERAGE_HIGH")
    if dominant_action_pct > limits.max_dominant_action_pct:
        reasons.append("EDGE_ACTION_SIDE_IMBALANCE_HIGH")
    if mean_edge < limits.min_mean_net_edge_bps:
        reasons.append("EDGE_EXPECTED_EDGE_LOW")
    if median_edge < limits.min_median_net_edge_bps:
        reasons.append("EDGE_MEDIAN_EDGE_LOW")
    if win_rate < limits.min_win_rate_pct:
        reasons.append("EDGE_WIN_RATE_LOW")
    if pf < limits.min_profit_factor:
        reasons.append("EDGE_PROFIT_FACTOR_LOW")
    if max_dd > limits.max_drawdown_pct:
        reasons.append("EDGE_MAX_DRAWDOWN_HIGH")
    if oos_edge < limits.min_oos_mean_net_edge_bps:
        reasons.append("EDGE_OOS_EDGE_LOW")
    if wf_positive < limits.min_walk_forward_positive_rate_pct:
        reasons.append("EDGE_WALK_FORWARD_STABILITY_LOW")
    for metric_name, pct in coverage.items():
        if pct < limits.min_metric_coverage_pct and spec.family != "diagnostic":
            reasons.append(f"EDGE_{metric_name.upper()}_COVERAGE_LOW")
    if not spec.approvable:
        reasons.append("DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if mean_edge > 0.0 and reasons:
        warnings.append("EDGE_POSITIVE_BUT_BELOW_GATE")

    decision = "PASS" if not reasons else "BLOCK"
    score = round(
        mean_edge * 3.0
        + median_edge * 1.5
        + (pf - 1.0) * 25.0
        + (win_rate - 50.0) * 0.5
        + oos_edge * 2.0
        + wf_positive * 0.2
        - max_dd * 1.5
        - abs(signal_coverage_pct - 6.0) * 0.4
        - max(0.0, dominant_action_pct - 60.0) * 0.5,
        6,
    )

    return FuturesEdgeEvaluation(
        contract_version=FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION,
        decision=decision,
        ok=decision == "PASS",
        symbol=symbol,
        interval=interval,
        strategy=spec.name,
        family=spec.family,
        approvable=spec.approvable,
        score=score,
        clean_samples=clean_samples,
        signal_count=signal_count,
        signal_coverage_pct=signal_coverage_pct,
        buy_count=buy_count,
        sell_count=sell_count,
        dominant_action_pct=dominant_action_pct,
        mean_net_edge_bps=mean_edge,
        median_net_edge_bps=median_edge,
        win_rate_pct=win_rate,
        profit_factor=pf,
        max_drawdown_pct=max_dd,
        oos_mean_net_edge_bps=oos_edge,
        walk_forward_positive_rate_pct=wf_positive,
        metric_coverage=coverage,
        reason_codes=reasons,
        warnings=warnings,
    )


def select_best_evaluation(evaluations: Iterable[FuturesEdgeEvaluation]) -> FuturesEdgeEvaluation | None:
    values = list(evaluations)
    if not values:
        return None
    passed = [item for item in values if item.ok]
    pool = passed if passed else values
    return sorted(pool, key=lambda item: item.score, reverse=True)[0]


def build_futures_funding_open_interest_edge_exploration(
    datasets: dict[tuple[str, str], pd.DataFrame],
    *,
    source: str,
    limits: FuturesEdgeLimits | None = None,
    specs: list[FuturesEdgeSpec] | None = None,
) -> dict[str, Any]:
    limits = limits or FuturesEdgeLimits()
    specs = specs or default_futures_edge_specs()
    evaluations: list[FuturesEdgeEvaluation] = []
    for (symbol, interval), frame in datasets.items():
        for spec in specs:
            try:
                evaluations.append(evaluate_futures_strategy_edge(frame, spec, symbol=symbol, interval=interval, limits=limits))
            except Exception as exc:  # defensive report entry instead of aborting whole sweep
                evaluations.append(
                    FuturesEdgeEvaluation(
                        contract_version=FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION,
                        decision="BLOCK",
                        ok=False,
                        symbol=symbol,
                        interval=interval,
                        strategy=spec.name,
                        family=spec.family,
                        approvable=spec.approvable,
                        score=-9999.0,
                        clean_samples=0,
                        signal_count=0,
                        signal_coverage_pct=0.0,
                        buy_count=0,
                        sell_count=0,
                        dominant_action_pct=0.0,
                        mean_net_edge_bps=0.0,
                        median_net_edge_bps=0.0,
                        win_rate_pct=0.0,
                        profit_factor=0.0,
                        max_drawdown_pct=0.0,
                        oos_mean_net_edge_bps=0.0,
                        walk_forward_positive_rate_pct=0.0,
                        metric_coverage={},
                        reason_codes=["EDGE_EVALUATION_ERROR"],
                        warnings=[str(exc)[:240]],
                    )
                )
    selected = select_best_evaluation(evaluations)
    pass_count = sum(1 for item in evaluations if item.ok)
    decision = "PASS" if pass_count > 0 else "BLOCK"
    reasons = [] if decision == "PASS" else ["NO_FUTURES_FUNDING_OI_EDGE_CANDIDATE_PASSED"]
    if selected and selected.reason_codes:
        reasons.extend(code for code in selected.reason_codes if code not in reasons)

    recommendation = (
        "A futures funding/open-interest edge candidate passed the research gate. Treat it only as a research candidate; "
        "do not train, reload, paper trade, or enable live trading yet."
        if decision == "PASS"
        else "No futures funding/open-interest strategy showed enough net edge. Revisit futures behaviour features, market, timeframe, or hypothesis before further ML work."
    )

    return {
        "contract_version": FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION,
        "phase": FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION,
        "report_type": "futures_funding_open_interest_edge_exploration",
        "decision": decision,
        "ok": decision == "PASS",
        "source": source,
        "candidate_count": len(evaluations),
        "approved_for_research_candidate": decision == "PASS",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "observation_only": True,
        "get_only_public_futures_data": True,
        "post_requests_allowed": False,
        "reason_codes": reasons,
        "recommendation": recommendation,
        "selected": asdict(selected) if selected else None,
        "candidates": [asdict(item) for item in sorted(evaluations, key=lambda item: item.score, reverse=True)],
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "get_only_public_futures_data": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def render_futures_edge_markdown(report: dict[str, Any]) -> str:
    selected = report.get("selected") or {}
    lines = [
        f"# {report['contract_version']} Futures Funding / Open Interest Edge Exploration",
        "",
        f"- contract_version: `{report['contract_version']}`",
        f"- decision: **{report['decision']}**",
        f"- source: `{report['source']}`",
        f"- candidate_count: `{report['candidate_count']}`",
        f"- approved_for_research_candidate: `{report['approved_for_research_candidate']}`",
        f"- approved_for_training_candidate: `{report['approved_for_training_candidate']}`",
        f"- approved_for_paper_candidate: `{report['approved_for_paper_candidate']}`",
        f"- approved_for_live_real: `{report['approved_for_live_real']}`",
    ]
    if selected:
        lines.extend(
            [
                f"- selected: `{selected.get('symbol')}` `{selected.get('interval')}` `{selected.get('strategy')}`",
                f"- selected_mean_net_edge_bps: `{selected.get('mean_net_edge_bps')}`",
                f"- selected_profit_factor: `{selected.get('profit_factor')}`",
            ]
        )
    lines.extend([f"- recommendation: {report['recommendation']}", "", "## Guardrails", ""])
    for key, value in report.get("guardrails", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Candidates",
            "",
            "| # | decision | score | symbol | interval | strategy | signals | coverage_pct | mean_edge_bps | median_edge_bps | win_rate_pct | profit_factor | max_dd_pct | oos_edge_bps | reasons | warnings |",
            "|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for idx, item in enumerate(report.get("candidates", []), start=1):
        lines.append(
            "| {idx} | {decision} | {score} | {symbol} | {interval} | {strategy} | {signals} | {coverage} | {mean} | {median} | {win} | {pf} | {dd} | {oos} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=item.get("decision"),
                score=item.get("score"),
                symbol=item.get("symbol"),
                interval=item.get("interval"),
                strategy=item.get("strategy"),
                signals=item.get("signal_count"),
                coverage=item.get("signal_coverage_pct"),
                mean=item.get("mean_net_edge_bps"),
                median=item.get("median_net_edge_bps"),
                win=item.get("win_rate_pct"),
                pf=item.get("profit_factor"),
                dd=item.get("max_drawdown_pct"),
                oos=item.get("oos_mean_net_edge_bps"),
                reasons=item.get("reason_codes", []),
                warnings=item.get("warnings", []),
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "This tool uses public Binance USDⓈ-M futures market data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate for the next controlled phase; paper/live trading remains blocked.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report_files(report: dict[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    import json

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_path / f"{REPORT_PREFIX}_{ts}.json"
    md_path = out_path / f"{REPORT_PREFIX}_{ts}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_futures_edge_markdown(report), encoding="utf-8")
    return json_path, md_path
