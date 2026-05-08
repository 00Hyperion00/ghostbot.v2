from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION = "4B.4.3.6.6.25A"
REPORT_TYPE = "higher_timeframe_trend_edge_exploration"
PHASE = "4B.4.3.6.6.25A"

# Guardrail markers intentionally kept explicit for release/acceptance checks.
get_only_public_market_data = True
post_requests_allowed = False
approved_for_live_real = False

BUY = 1
SELL = -1
HOLD = 0


@dataclass(frozen=True)
class HigherTimeframeStrategySpec:
    name: str
    family: str
    approvable: bool = True
    description: str = ""


@dataclass(frozen=True)
class HigherTimeframeTrendLimits:
    min_clean_samples: int = 300
    min_signal_count: int = 60
    min_signal_coverage_pct: float = 0.5
    max_signal_coverage_pct: float = 35.0
    max_dominant_action_pct: float = 78.0
    min_mean_net_edge_bps: float = 3.0
    min_median_net_edge_bps: float = 0.0
    min_win_rate_pct: float = 44.0
    min_profit_factor: float = 1.15
    max_drawdown_pct: float = 8.0
    min_oos_mean_net_edge_bps: float = 1.0
    min_walk_forward_positive_rate_pct: float = 55.0


@dataclass(frozen=True)
class StrategyEvaluation:
    contract_version: str
    symbol: str
    interval: str
    strategy: str
    family: str
    approvable: bool
    decision: str
    ok: bool
    reason_codes: list[str]
    warnings: list[str]
    score: float
    clean_samples: int
    signal_count: int
    buy_count: int
    sell_count: int
    signal_coverage_pct: float
    dominant_action_pct: float
    mean_net_edge_bps: float
    median_net_edge_bps: float
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    oos_mean_net_edge_bps: float
    walk_forward_positive_rate_pct: float
    cost_bps: float
    lookahead_bars: int


DEFAULT_STRATEGY_SPECS: tuple[HigherTimeframeStrategySpec, ...] = (
    HigherTimeframeStrategySpec(
        name="ema_trend_continuation",
        family="trend_following",
        description="EMA20/EMA50/EMA200 directional continuation with RSI guard.",
    ),
    HigherTimeframeStrategySpec(
        name="atr_breakout_volume",
        family="breakout",
        description="ATR-adjusted Donchian breakout confirmed by volume.",
    ),
    HigherTimeframeStrategySpec(
        name="pullback_to_vwap_in_trend",
        family="trend_pullback",
        description="VWAP/ATR pullback inside higher-timeframe EMA trend.",
    ),
    HigherTimeframeStrategySpec(
        name="volatility_compression_breakout",
        family="volatility_breakout",
        description="Bollinger-width compression followed by directional breakout.",
    ),
)


INTERVAL_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "8h": 480,
    "12h": 720,
    "1d": 1440,
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _round(value: float, digits: int = 6) -> float:
    return round(_safe_float(value), digits)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=max(2, span // 2)).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain > 0.0)), 100.0)
    rsi = rsi.where(~((avg_loss == 0.0) & (avg_gain == 0.0)), 50.0)
    return rsi


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"OHLCV dataset missing columns: {sorted(missing)}")

    out = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close", "volume"]).reset_index(drop=True)
    out = out[out["close"] > 0].copy()
    out = out.reset_index(drop=True)

    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"].clip(lower=0.0)

    out["ema_20"] = _ema(close, 20)
    out["ema_50"] = _ema(close, 50)
    out["ema_200"] = _ema(close, 200)
    out["rsi_14"] = _rsi(close, 14)
    out["atr_14"] = _atr(out, 14)
    out["atr_pct"] = (out["atr_14"] / close.replace(0.0, np.nan)) * 100.0
    typical = (high + low + close) / 3.0
    vol_sum = volume.cumsum().replace(0.0, np.nan)
    out["vwap"] = (typical * volume).cumsum() / vol_sum
    out["close_to_vwap_atr"] = (close - out["vwap"]) / out["atr_14"].replace(0.0, np.nan)
    out["vol_sma_20"] = volume.rolling(20, min_periods=5).mean()
    out["donchian_high_20"] = high.rolling(20, min_periods=10).max().shift(1)
    out["donchian_low_20"] = low.rolling(20, min_periods=10).min().shift(1)
    bb_mid = close.rolling(20, min_periods=10).mean()
    bb_std = close.rolling(20, min_periods=10).std(ddof=0)
    out["bb_upper"] = bb_mid + 2 * bb_std
    out["bb_lower"] = bb_mid - 2 * bb_std
    out["bb_width_pct"] = ((out["bb_upper"] - out["bb_lower"]) / bb_mid.replace(0.0, np.nan)) * 100.0
    out["bb_width_q25_120"] = out["bb_width_pct"].rolling(120, min_periods=30).quantile(0.25)
    out["range_atr_ratio"] = (high - low) / out["atr_14"].replace(0.0, np.nan)
    return out


def _lookahead_for_interval(interval: str) -> int:
    minutes = INTERVAL_MINUTES.get(interval, 60)
    if minutes <= 15:
        return 4
    if minutes <= 60:
        return 3
    return 2


def _strategy_signals(df: pd.DataFrame, strategy: str) -> pd.Series:
    close = df["close"]
    signal = pd.Series(HOLD, index=df.index, dtype="int64")

    if strategy == "ema_trend_continuation":
        up = (
            (close > df["ema_20"])
            & (df["ema_20"] > df["ema_50"])
            & (df["ema_50"] > df["ema_200"])
            & (df["rsi_14"].between(48.0, 100.1))
        )
        down = (
            (close < df["ema_20"])
            & (df["ema_20"] < df["ema_50"])
            & (df["ema_50"] < df["ema_200"])
            & (df["rsi_14"].between(-0.1, 52.0))
        )
        signal.loc[up] = BUY
        signal.loc[down] = SELL
        return signal

    if strategy == "atr_breakout_volume":
        atr = df["atr_14"]
        high_break = close > (df["donchian_high_20"] + 0.15 * atr)
        low_break = close < (df["donchian_low_20"] - 0.15 * atr)
        volume_confirm = df["volume"] > 1.05 * df["vol_sma_20"]
        trend_up = df["ema_50"] >= df["ema_200"]
        trend_down = df["ema_50"] <= df["ema_200"]
        signal.loc[high_break & volume_confirm & trend_up] = BUY
        signal.loc[low_break & volume_confirm & trend_down] = SELL
        return signal

    if strategy == "pullback_to_vwap_in_trend":
        near_vwap = df["close_to_vwap_atr"].abs() <= 0.75
        up = (df["ema_50"] > df["ema_200"]) & (close > df["ema_200"]) & near_vwap & (df["rsi_14"] >= 44.0)
        down = (df["ema_50"] < df["ema_200"]) & (close < df["ema_200"]) & near_vwap & (df["rsi_14"] <= 56.0)
        signal.loc[up] = BUY
        signal.loc[down] = SELL
        return signal

    if strategy == "volatility_compression_breakout":
        compressed = df["bb_width_pct"] <= df["bb_width_q25_120"]
        prior_high = df["high"].rolling(8, min_periods=4).max().shift(1)
        prior_low = df["low"].rolling(8, min_periods=4).min().shift(1)
        break_up = (close > prior_high) & (close > df["ema_50"])
        break_down = (close < prior_low) & (close < df["ema_50"])
        signal.loc[compressed & break_up] = BUY
        signal.loc[compressed & break_down] = SELL
        return signal

    if strategy == "diagnostic_every_trend_tick":
        signal.loc[(df["ema_50"] > df["ema_200"])] = BUY
        signal.loc[(df["ema_50"] < df["ema_200"])] = SELL
        return signal

    raise ValueError(f"Unknown strategy: {strategy}")


def _max_drawdown_pct(net_edges_bps: pd.Series) -> float:
    if net_edges_bps.empty:
        return 0.0
    equity_pct = net_edges_bps.cumsum() / 100.0
    running_max = equity_pct.cummax()
    drawdown = running_max - equity_pct
    return _safe_float(drawdown.max(), 0.0)


def _profit_factor(net_edges_bps: pd.Series) -> float:
    positive = net_edges_bps[net_edges_bps > 0].sum()
    negative = net_edges_bps[net_edges_bps < 0].sum()
    if negative == 0:
        return 999.0 if positive > 0 else 0.0
    return _safe_float(positive / abs(negative), 0.0)


def _walk_forward_positive_rate(edges: pd.Series, folds: int = 4) -> float:
    if edges.empty:
        return 0.0
    chunks = np.array_split(edges.to_numpy(dtype=float), folds)
    valid = [chunk for chunk in chunks if len(chunk) > 0]
    if not valid:
        return 0.0
    positive = sum(1 for chunk in valid if float(np.mean(chunk)) > 0.0)
    return 100.0 * positive / len(valid)


def _score(metrics: dict[str, float], limits: HigherTimeframeTrendLimits) -> float:
    return _round(
        metrics["mean_net_edge_bps"] * 6.0
        + metrics["median_net_edge_bps"] * 2.0
        + (metrics["profit_factor"] - 1.0) * 18.0
        + (metrics["win_rate_pct"] - 50.0) * 0.4
        + metrics["oos_mean_net_edge_bps"] * 4.0
        + (metrics["walk_forward_positive_rate_pct"] - limits.min_walk_forward_positive_rate_pct) * 0.3
        - max(0.0, metrics["max_drawdown_pct"] - limits.max_drawdown_pct) * 8.0
        - abs(metrics["signal_coverage_pct"] - 10.0) * 0.15,
        6,
    )


def evaluate_strategy_edge(
    df: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    spec: HigherTimeframeStrategySpec,
    cost_bps: float = 16.0,
    lookahead_bars: int | None = None,
    limits: HigherTimeframeTrendLimits | None = None,
) -> StrategyEvaluation:
    limits = limits or HigherTimeframeTrendLimits()
    prepared = _prepare_ohlcv(df)
    lookahead = lookahead_bars if lookahead_bars is not None else _lookahead_for_interval(interval)
    clean_samples = int(len(prepared))
    reason_codes: list[str] = []
    warnings: list[str] = []

    if clean_samples < limits.min_clean_samples:
        reason_codes.append("EDGE_SAMPLE_COUNT_LOW")

    signal = _strategy_signals(prepared, spec.name)
    future_return = prepared["close"].shift(-lookahead) / prepared["close"] - 1.0
    signed_return = signal.astype(float) * future_return.astype(float)
    net_edge_bps_all = signed_return * 10000.0 - float(cost_bps)
    valid = (signal != HOLD) & net_edge_bps_all.notna()
    edge = net_edge_bps_all.loc[valid].astype(float)

    signal_count = int(valid.sum())
    buy_count = int(((signal == BUY) & valid).sum())
    sell_count = int(((signal == SELL) & valid).sum())
    coverage = 100.0 * signal_count / max(1, clean_samples)
    dominant = 0.0 if signal_count == 0 else 100.0 * max(buy_count, sell_count) / signal_count
    mean_edge = _safe_float(edge.mean(), 0.0)
    median_edge = _safe_float(edge.median(), 0.0)
    win_rate = 0.0 if edge.empty else 100.0 * float((edge > 0).mean())
    pf = _profit_factor(edge)
    dd = _max_drawdown_pct(edge)

    if signal_count > 0:
        split = int(len(edge) * 0.7)
        oos_edge = edge.iloc[split:] if split < len(edge) else edge.iloc[0:0]
    else:
        oos_edge = edge
    oos_mean = _safe_float(oos_edge.mean(), 0.0)
    wf_positive = _walk_forward_positive_rate(edge)

    if not spec.approvable:
        reason_codes.append("DIAGNOSTIC_STRATEGY_NOT_APPROVABLE")
    if signal_count < limits.min_signal_count:
        reason_codes.append("EDGE_SIGNAL_COUNT_LOW")
    if coverage < limits.min_signal_coverage_pct:
        reason_codes.append("EDGE_COVERAGE_LOW")
    if coverage > limits.max_signal_coverage_pct:
        reason_codes.append("EDGE_COVERAGE_HIGH")
    if dominant > limits.max_dominant_action_pct:
        reason_codes.append("EDGE_ACTION_SIDE_IMBALANCE_HIGH")
    if mean_edge < limits.min_mean_net_edge_bps:
        reason_codes.append("EDGE_EXPECTED_EDGE_LOW")
    if median_edge < limits.min_median_net_edge_bps:
        reason_codes.append("EDGE_MEDIAN_EDGE_LOW")
    if win_rate < limits.min_win_rate_pct:
        reason_codes.append("EDGE_WIN_RATE_LOW")
    if pf < limits.min_profit_factor:
        reason_codes.append("EDGE_PROFIT_FACTOR_LOW")
    if dd > limits.max_drawdown_pct:
        reason_codes.append("EDGE_MAX_DRAWDOWN_HIGH")
    if oos_mean < limits.min_oos_mean_net_edge_bps:
        reason_codes.append("EDGE_OOS_EDGE_LOW")
    if wf_positive < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("EDGE_WALK_FORWARD_STABILITY_LOW")

    if limits.min_signal_count <= signal_count < limits.min_signal_count * 1.25:
        warnings.append("EDGE_SIGNAL_COUNT_NEAR_FLOOR")
    if 0.0 <= mean_edge < limits.min_mean_net_edge_bps:
        warnings.append("EDGE_POSITIVE_BUT_BELOW_GATE")

    metrics = {
        "mean_net_edge_bps": mean_edge,
        "median_net_edge_bps": median_edge,
        "profit_factor": pf,
        "win_rate_pct": win_rate,
        "oos_mean_net_edge_bps": oos_mean,
        "walk_forward_positive_rate_pct": wf_positive,
        "max_drawdown_pct": dd,
        "signal_coverage_pct": coverage,
    }
    score = _score(metrics, limits)
    ok = not reason_codes
    return StrategyEvaluation(
        contract_version=HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION,
        symbol=symbol,
        interval=interval,
        strategy=spec.name,
        family=spec.family,
        approvable=spec.approvable,
        decision="PASS" if ok else "BLOCK",
        ok=ok,
        reason_codes=reason_codes,
        warnings=warnings,
        score=score,
        clean_samples=clean_samples,
        signal_count=signal_count,
        buy_count=buy_count,
        sell_count=sell_count,
        signal_coverage_pct=_round(coverage),
        dominant_action_pct=_round(dominant),
        mean_net_edge_bps=_round(mean_edge),
        median_net_edge_bps=_round(median_edge),
        win_rate_pct=_round(win_rate),
        profit_factor=_round(pf),
        max_drawdown_pct=_round(dd),
        oos_mean_net_edge_bps=_round(oos_mean),
        walk_forward_positive_rate_pct=_round(wf_positive),
        cost_bps=_round(cost_bps),
        lookahead_bars=int(lookahead),
    )


def _aggregate_reason_codes(candidates: Iterable[StrategyEvaluation]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for candidate in candidates:
        for code in candidate.reason_codes:
            if code not in seen:
                seen.add(code)
                out.append(code)
    return out


def build_timeframe_symbol_strategy_edge_exploration(
    datasets: dict[tuple[str, str], pd.DataFrame],
    *,
    source: str,
    cost_bps: float = 16.0,
    strategy_specs: Iterable[HigherTimeframeStrategySpec] | None = None,
    limits: HigherTimeframeTrendLimits | None = None,
) -> dict[str, Any]:
    limits = limits or HigherTimeframeTrendLimits()
    specs = tuple(strategy_specs or DEFAULT_STRATEGY_SPECS)
    evaluations: list[StrategyEvaluation] = []

    for (symbol, interval), df in datasets.items():
        for spec in specs:
            try:
                evaluations.append(
                    evaluate_strategy_edge(
                        df,
                        symbol=symbol,
                        interval=interval,
                        spec=spec,
                        cost_bps=cost_bps,
                        limits=limits,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive report path
                evaluations.append(
                    StrategyEvaluation(
                        contract_version=HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION,
                        symbol=symbol,
                        interval=interval,
                        strategy=spec.name,
                        family=spec.family,
                        approvable=spec.approvable,
                        decision="BLOCK",
                        ok=False,
                        reason_codes=["EDGE_EVALUATION_ERROR"],
                        warnings=[f"{type(exc).__name__}: {exc}"],
                        score=-9999.0,
                        clean_samples=0,
                        signal_count=0,
                        buy_count=0,
                        sell_count=0,
                        signal_coverage_pct=0.0,
                        dominant_action_pct=0.0,
                        mean_net_edge_bps=0.0,
                        median_net_edge_bps=0.0,
                        win_rate_pct=0.0,
                        profit_factor=0.0,
                        max_drawdown_pct=0.0,
                        oos_mean_net_edge_bps=0.0,
                        walk_forward_positive_rate_pct=0.0,
                        cost_bps=_round(cost_bps),
                        lookahead_bars=0,
                    )
                )

    candidates = sorted(evaluations, key=lambda item: item.score, reverse=True)
    selected = next((candidate for candidate in candidates if candidate.ok), candidates[0] if candidates else None)
    approved_for_research_candidate = bool(selected and selected.ok)
    terminal_reason_codes = [] if approved_for_research_candidate else ["NO_HIGHER_TIMEFRAME_TREND_EDGE_CANDIDATE_PASSED"]
    terminal_reason_codes.extend(_aggregate_reason_codes(candidates[:12]))
    terminal_reason_codes = list(dict.fromkeys(terminal_reason_codes))

    decision = "RESEARCH_CANDIDATE" if approved_for_research_candidate else "BLOCK"
    recommendation = (
        "A higher-timeframe trend edge candidate passed the research gate. Keep training/paper/live blocked; open only the next controlled research phase."
        if approved_for_research_candidate
        else "No higher-timeframe trend strategy showed enough net edge. Do not train, promote, start paper trading, or enable live trading from this hypothesis."
    )

    return {
        "contract_version": HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION,
        "phase": PHASE,
        "report_type": REPORT_TYPE,
        "decision": decision,
        "ok": approved_for_research_candidate,
        "source": source,
        "candidate_count": len(candidates),
        "approved_for_research_candidate": approved_for_research_candidate,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "get_only_public_market_data": True,
        "reason_codes": terminal_reason_codes,
        "recommendation": recommendation,
        "selected": asdict(selected) if selected else None,
        "candidates": [asdict(candidate) for candidate in candidates],
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "get_only_public_market_data": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "backtest_pass_is_not_paper_permission": True,
            "paper_pass_is_not_live_permission": True,
        },
    }


def render_timeframe_symbol_strategy_edge_markdown(report: dict[str, Any]) -> str:
    selected = report.get("selected") or {}
    lines = [
        "# 4B.4.3.6.6.25A Higher Timeframe Trend Edge Exploration",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- source: `{report.get('source')}`",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected: `{selected.get('symbol', '-')}` `{selected.get('interval', '-')}` `{selected.get('strategy', '-')}`",
        f"- selected_mean_net_edge_bps: `{selected.get('mean_net_edge_bps', 0)}`",
        f"- selected_profit_factor: `{selected.get('profit_factor', 0)}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in (report.get("guardrails") or {}).items():
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
    for idx, candidate in enumerate(report.get("candidates", [])[:80], start=1):
        lines.append(
            "| {idx} | {decision} | {score} | {symbol} | {interval} | {strategy} | {signals} | {coverage} | {mean_edge} | {median_edge} | {win_rate} | {pf} | {dd} | {oos} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=candidate.get("decision"),
                score=candidate.get("score"),
                symbol=candidate.get("symbol"),
                interval=candidate.get("interval"),
                strategy=candidate.get("strategy"),
                signals=candidate.get("signal_count"),
                coverage=candidate.get("signal_coverage_pct"),
                mean_edge=candidate.get("mean_net_edge_bps"),
                median_edge=candidate.get("median_net_edge_bps"),
                win_rate=candidate.get("win_rate_pct"),
                pf=candidate.get("profit_factor"),
                dd=candidate.get("max_drawdown_pct"),
                oos=candidate.get("oos_mean_net_edge_bps"),
                reasons=candidate.get("reason_codes", []),
                warnings=candidate.get("warnings", []),
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "This tool uses public market data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate for the next controlled phase; paper/live trading remains blocked.",
            "",
        ]
    )
    return "\n".join(lines)
