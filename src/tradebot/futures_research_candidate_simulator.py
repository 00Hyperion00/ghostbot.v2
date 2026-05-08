from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION = "4B.4.3.6.6.25D"
REPORT_PREFIX = "4B436625D_futures_research_candidate_simulator"

DEFAULT_CANDIDATE_SYMBOL = "BTCUSDT"
DEFAULT_CANDIDATE_INTERVAL = "4h"
DEFAULT_CANDIDATE_STRATEGY = "funding_trend_exhaustion"


@dataclass(frozen=True)
class FuturesResearchCandidateSpec:
    hypothesis_id: str = "HYP-002"
    symbol: str = DEFAULT_CANDIDATE_SYMBOL
    interval: str = DEFAULT_CANDIDATE_INTERVAL
    strategy: str = DEFAULT_CANDIDATE_STRATEGY
    comparator_symbols: tuple[str, ...] = ("ETHUSDT",)
    source_phase: str = "4B.4.3.6.6.25C"
    cost_bps: float = 16.0
    slippage_bps: float = 4.0
    hold_bars: int = 3
    funding_quantile: float = 0.75
    trend_ema_fast: int = 21
    trend_ema_slow: int = 55
    use_optional_futures_metrics: bool = True
    approvable: bool = True

    @property
    def round_trip_cost_bps(self) -> float:
        return float(self.cost_bps + self.slippage_bps)


@dataclass(frozen=True)
class DryRunSimulatorLimits:
    min_rows: int = 120
    min_signal_count: int = 30
    min_signal_coverage_pct: float = 0.5
    max_signal_coverage_pct: float = 20.0
    max_dominant_action_pct: float = 78.0
    min_mean_net_edge_bps: float = 0.0
    min_median_net_edge_bps: float = 0.0
    min_profit_factor: float = 1.15
    min_win_rate_pct: float = 45.0
    max_drawdown_pct: float = 25.0
    min_oos_mean_net_edge_bps: float = 0.0
    min_walk_forward_positive_rate_pct: float = 60.0
    min_funding_coverage_pct: float = 85.0
    max_top_trade_edge_share_pct: float = 45.0


@dataclass(frozen=True)
class DryRunTrade:
    entry_time: str
    exit_time: str
    side: str
    entry_price: float
    exit_price: float
    gross_edge_bps: float
    net_edge_bps: float
    reason: str
    funding_rate: float | None = None
    open_interest: float | None = None
    long_short_ratio: float | None = None
    taker_buy_sell_ratio: float | None = None


@dataclass(frozen=True)
class DryRunCandidateResult:
    contract_version: str
    decision: str
    ok: bool
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    reload_allowed: bool
    reason_codes: list[str]
    warnings: list[str]
    score: float
    spec: dict[str, Any]
    metrics: dict[str, Any]
    trades: list[dict[str, Any]]


@dataclass(frozen=True)
class DryRunSimulatorReport:
    contract_version: str
    phase: str
    report_type: str
    decision: str
    ok: bool
    source: str
    selected: dict[str, Any]
    approved_for_research_candidate: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_allowed: bool
    reload_performed: bool
    config_mutation_performed: bool
    order_actions_performed: bool
    no_post_actions: bool
    observation_only: bool
    reason_codes: list[str]
    warnings: list[str]
    recommendation: str
    candidate: dict[str, Any]
    guardrails: dict[str, Any]


def _utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_candidate_spec_from_robustness_report(report: Mapping[str, Any]) -> FuturesResearchCandidateSpec:
    """Build the 25D dry-run spec from a 25C robustness report.

    The parser is intentionally tolerant because earlier research reports may expose
    selected fields either at top level, inside `selection.best_candidate`, or inside
    a flat candidate table. 25C PASS should normally select BTCUSDT 4h
    funding_trend_exhaustion, with ETHUSDT as a useful comparator.
    """
    selected = report.get("selected") if isinstance(report.get("selected"), Mapping) else {}
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}

    symbol = (
        selected.get("symbol")
        or best.get("symbol")
        or report.get("selected_symbol")
        or report.get("symbol")
        or DEFAULT_CANDIDATE_SYMBOL
    )
    interval = (
        selected.get("interval")
        or best.get("interval")
        or report.get("selected_interval")
        or report.get("interval")
        or DEFAULT_CANDIDATE_INTERVAL
    )
    strategy = (
        selected.get("strategy")
        or best.get("strategy")
        or report.get("selected_strategy")
        or report.get("strategy")
        or DEFAULT_CANDIDATE_STRATEGY
    )

    candidates = _as_list(report.get("candidates"))
    pass_symbols: list[str] = []
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("decision", "")).upper() != "PASS":
            continue
        item_symbol = str(item.get("symbol") or "").upper()
        item_strategy = str(item.get("strategy") or "")
        item_interval = str(item.get("interval") or "")
        if item_symbol and item_symbol != str(symbol).upper() and item_strategy == strategy and item_interval == interval:
            pass_symbols.append(item_symbol)
    comparator_symbols = tuple(dict.fromkeys(pass_symbols or ["ETHUSDT" if str(symbol).upper() != "ETHUSDT" else "BTCUSDT"]))

    return FuturesResearchCandidateSpec(
        symbol=str(symbol).upper(),
        interval=str(interval),
        strategy=str(strategy),
        comparator_symbols=comparator_symbols,
    )


def normalize_market_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    rename_map = {
        "open_time": "timestamp",
        "time": "timestamp",
        "date": "timestamp",
        "funding_rate": "fundingRate",
        "sum_open_interest": "sumOpenInterest",
        "long_short_ratio": "longShortRatio",
        "buy_sell_ratio": "buySellRatio",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})
    if "timestamp" not in out.columns:
        if "close_time" in out.columns:
            out["timestamp"] = out["close_time"]
        else:
            out["timestamp"] = np.arange(len(out), dtype=np.int64)
    if pd.api.types.is_numeric_dtype(out["timestamp"]):
        # Tolerate seconds or milliseconds.
        max_ts = float(pd.to_numeric(out["timestamp"], errors="coerce").max())
        unit = "ms" if max_ts > 10_000_000_000 else "s"
        out["timestamp"] = pd.to_datetime(out["timestamp"], unit=unit, utc=True, errors="coerce")
    else:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    for column in ["open", "high", "low", "close", "volume", "fundingRate", "sumOpenInterest", "longShortRatio", "buySellRatio"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    for required in ["open", "high", "low", "close", "volume"]:
        if required not in out.columns:
            raise ValueError(f"Missing required OHLCV column: {required}")
    return out.sort_values("timestamp").dropna(subset=["timestamp", "open", "high", "low", "close"]).reset_index(drop=True)


def enrich_research_features(df: pd.DataFrame, spec: FuturesResearchCandidateSpec) -> pd.DataFrame:
    out = normalize_market_dataframe(df)
    if out.empty:
        return out
    out["ema_fast"] = out["close"].ewm(span=spec.trend_ema_fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=spec.trend_ema_slow, adjust=False).mean()
    out["ema_spread_pct"] = (out["ema_fast"] - out["ema_slow"]) / out["close"].replace(0, np.nan) * 100.0
    out["return_1"] = out["close"].pct_change()
    out["realized_vol"] = out["return_1"].rolling(20, min_periods=5).std()
    out["volume_ratio"] = out["volume"] / out["volume"].rolling(40, min_periods=5).mean()
    if "fundingRate" not in out.columns:
        out["fundingRate"] = 0.0
    if "sumOpenInterest" not in out.columns:
        out["sumOpenInterest"] = np.nan
    if "longShortRatio" not in out.columns:
        out["longShortRatio"] = np.nan
    if "buySellRatio" not in out.columns:
        out["buySellRatio"] = np.nan
    out["fundingRate"] = out["fundingRate"].ffill().fillna(0.0)
    out["funding_abs"] = out["fundingRate"].abs()
    out["funding_pos_threshold"] = out["fundingRate"].rolling(120, min_periods=20).quantile(spec.funding_quantile)
    out["funding_neg_threshold"] = out["fundingRate"].rolling(120, min_periods=20).quantile(1.0 - spec.funding_quantile)
    return out


def _side_counts(sides: Sequence[str]) -> tuple[int, int, float]:
    buy_count = sum(1 for side in sides if side == "BUY")
    sell_count = sum(1 for side in sides if side == "SELL")
    total = buy_count + sell_count
    dominant = 0.0 if total <= 0 else max(buy_count, sell_count) / total * 100.0
    return buy_count, sell_count, dominant


def generate_funding_trend_exhaustion_signals(df: pd.DataFrame, spec: FuturesResearchCandidateSpec) -> list[tuple[int, str, str]]:
    enriched = enrich_research_features(df, spec)
    if enriched.empty:
        return []
    signals: list[tuple[int, str, str]] = []
    start_idx = max(spec.trend_ema_slow + 5, 30)
    for idx in range(start_idx, len(enriched) - spec.hold_bars - 1):
        row = enriched.iloc[idx]
        funding = _safe_float(row.get("fundingRate"))
        pos_threshold = _safe_float(row.get("funding_pos_threshold"), 0.0)
        neg_threshold = _safe_float(row.get("funding_neg_threshold"), 0.0)
        ema_spread = _safe_float(row.get("ema_spread_pct"), 0.0)
        volume_ratio = _safe_float(row.get("volume_ratio"), 1.0)
        # Crowded positive funding in an extended up trend -> exhaustion short.
        if funding > 0 and funding >= pos_threshold and ema_spread > 0 and volume_ratio >= 0.75:
            signals.append((idx, "SELL", "POSITIVE_FUNDING_TREND_EXHAUSTION"))
        # Crowded negative funding in an extended down trend -> exhaustion long.
        elif funding < 0 and funding <= neg_threshold and ema_spread < 0 and volume_ratio >= 0.75:
            signals.append((idx, "BUY", "NEGATIVE_FUNDING_TREND_EXHAUSTION"))
    return signals


def generate_dry_run_trades(df: pd.DataFrame, spec: FuturesResearchCandidateSpec) -> list[DryRunTrade]:
    enriched = enrich_research_features(df, spec)
    if enriched.empty:
        return []
    if spec.strategy != DEFAULT_CANDIDATE_STRATEGY:
        raise ValueError(f"Unsupported 25D strategy: {spec.strategy}")
    raw_signals = generate_funding_trend_exhaustion_signals(enriched, spec)
    trades: list[DryRunTrade] = []
    next_available_idx = 0
    for signal_idx, side, reason in raw_signals:
        entry_idx = signal_idx + 1
        exit_idx = entry_idx + spec.hold_bars
        if entry_idx < next_available_idx or exit_idx >= len(enriched):
            continue
        entry = enriched.iloc[entry_idx]
        exit_ = enriched.iloc[exit_idx]
        entry_price = _safe_float(entry["open"])
        exit_price = _safe_float(exit_["close"])
        if entry_price <= 0 or exit_price <= 0:
            continue
        direction = 1.0 if side == "BUY" else -1.0
        gross_edge_bps = direction * ((exit_price / entry_price) - 1.0) * 10_000.0
        net_edge_bps = gross_edge_bps - spec.round_trip_cost_bps
        trades.append(
            DryRunTrade(
                entry_time=str(entry["timestamp"]),
                exit_time=str(exit_["timestamp"]),
                side=side,
                entry_price=round(entry_price, 8),
                exit_price=round(exit_price, 8),
                gross_edge_bps=round(gross_edge_bps, 6),
                net_edge_bps=round(net_edge_bps, 6),
                reason=reason,
                funding_rate=None if pd.isna(enriched.iloc[signal_idx].get("fundingRate")) else round(_safe_float(enriched.iloc[signal_idx].get("fundingRate")), 10),
                open_interest=None if pd.isna(enriched.iloc[signal_idx].get("sumOpenInterest")) else round(_safe_float(enriched.iloc[signal_idx].get("sumOpenInterest")), 6),
                long_short_ratio=None if pd.isna(enriched.iloc[signal_idx].get("longShortRatio")) else round(_safe_float(enriched.iloc[signal_idx].get("longShortRatio")), 6),
                taker_buy_sell_ratio=None if pd.isna(enriched.iloc[signal_idx].get("buySellRatio")) else round(_safe_float(enriched.iloc[signal_idx].get("buySellRatio")), 6),
            )
        )
        next_available_idx = exit_idx + 1
    return trades


def _max_drawdown_pct(edge_bps: Sequence[float]) -> float:
    if not edge_bps:
        return 0.0
    equity = np.cumsum(np.array(edge_bps, dtype=float))
    peak = np.maximum.accumulate(equity)
    drawdown_bps = np.maximum(peak - equity, 0.0)
    return round(float(np.max(drawdown_bps) / 100.0), 6)


def _profit_factor(edge_bps: Sequence[float]) -> float:
    gains = sum(value for value in edge_bps if value > 0)
    losses = abs(sum(value for value in edge_bps if value < 0))
    if losses <= 0:
        return 99.0 if gains > 0 else 0.0
    return gains / losses


def _positive_window_rate(edge_bps: Sequence[float], windows: int = 4) -> float:
    if len(edge_bps) < windows:
        return 0.0
    splits = np.array_split(np.array(edge_bps, dtype=float), windows)
    positive = sum(1 for split in splits if len(split) and float(np.mean(split)) > 0.0)
    return positive / len(splits) * 100.0


def _oos_mean(edge_bps: Sequence[float]) -> float:
    if not edge_bps:
        return 0.0
    start = max(0, int(len(edge_bps) * 0.7))
    tail = list(edge_bps)[start:]
    return float(np.mean(tail)) if tail else 0.0


def _coverage_pct(df: pd.DataFrame, column: str) -> float:
    if len(df) == 0 or column not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").notna().mean() * 100.0)


def evaluate_dry_run_candidate(
    df: pd.DataFrame,
    spec: FuturesResearchCandidateSpec,
    limits: DryRunSimulatorLimits | None = None,
) -> DryRunCandidateResult:
    limits = limits or DryRunSimulatorLimits()
    enriched = enrich_research_features(df, spec)
    trades = generate_dry_run_trades(enriched, spec)
    edge_values = [trade.net_edge_bps for trade in trades]
    sides = [trade.side for trade in trades]
    buy_count, sell_count, dominant_action_pct = _side_counts(sides)
    signal_count = len(trades)
    signal_coverage_pct = 0.0 if len(enriched) == 0 else signal_count / len(enriched) * 100.0
    mean_edge = float(np.mean(edge_values)) if edge_values else 0.0
    median_edge = float(np.median(edge_values)) if edge_values else 0.0
    win_rate = sum(1 for value in edge_values if value > 0.0) / signal_count * 100.0 if signal_count else 0.0
    profit_factor = _profit_factor(edge_values)
    max_dd_pct = _max_drawdown_pct(edge_values)
    oos_edge = _oos_mean(edge_values)
    walk_forward_rate = _positive_window_rate(edge_values)
    top_trade_edge_share_pct = 0.0
    positive_sum = sum(value for value in edge_values if value > 0.0)
    if positive_sum > 0.0:
        top_trade_edge_share_pct = max([value for value in edge_values if value > 0.0] or [0.0]) / positive_sum * 100.0

    funding_coverage = _coverage_pct(enriched, "fundingRate")
    oi_coverage = _coverage_pct(enriched, "sumOpenInterest")
    long_short_coverage = _coverage_pct(enriched, "longShortRatio")
    taker_coverage = _coverage_pct(enriched, "buySellRatio")

    reason_codes: list[str] = []
    warnings: list[str] = []
    if len(enriched) < limits.min_rows:
        reason_codes.append("DRY_RUN_SAMPLE_COUNT_LOW")
    if signal_count < limits.min_signal_count:
        reason_codes.append("DRY_RUN_SIGNAL_COUNT_LOW")
    if signal_coverage_pct < limits.min_signal_coverage_pct:
        reason_codes.append("DRY_RUN_SIGNAL_COVERAGE_LOW")
    if signal_coverage_pct > limits.max_signal_coverage_pct:
        reason_codes.append("DRY_RUN_SIGNAL_COVERAGE_HIGH")
    if dominant_action_pct > limits.max_dominant_action_pct:
        reason_codes.append("DRY_RUN_ACTION_SIDE_IMBALANCE_HIGH")
    if mean_edge <= limits.min_mean_net_edge_bps:
        reason_codes.append("DRY_RUN_EXPECTED_EDGE_LOW")
    if median_edge <= limits.min_median_net_edge_bps:
        reason_codes.append("DRY_RUN_MEDIAN_EDGE_LOW")
    if win_rate < limits.min_win_rate_pct:
        reason_codes.append("DRY_RUN_WIN_RATE_LOW")
    if profit_factor < limits.min_profit_factor:
        reason_codes.append("DRY_RUN_PROFIT_FACTOR_LOW")
    if max_dd_pct > limits.max_drawdown_pct:
        reason_codes.append("DRY_RUN_MAX_DRAWDOWN_HIGH")
    if oos_edge <= limits.min_oos_mean_net_edge_bps:
        reason_codes.append("DRY_RUN_OOS_EDGE_LOW")
    if walk_forward_rate < limits.min_walk_forward_positive_rate_pct:
        reason_codes.append("DRY_RUN_WALK_FORWARD_STABILITY_LOW")
    if funding_coverage < limits.min_funding_coverage_pct:
        reason_codes.append("DRY_RUN_FUNDING_COVERAGE_LOW")
    if top_trade_edge_share_pct > limits.max_top_trade_edge_share_pct:
        reason_codes.append("DRY_RUN_OUTLIER_DEPENDENCY_HIGH")

    if oi_coverage <= 0:
        warnings.append("OPEN_INTEREST_COVERAGE_DETAIL_UNAVAILABLE")
    if long_short_coverage <= 0:
        warnings.append("LONG_SHORT_COVERAGE_DETAIL_UNAVAILABLE")
    if taker_coverage <= 0:
        warnings.append("TAKER_COVERAGE_DETAIL_UNAVAILABLE")
    if 0 < signal_count < limits.min_signal_count * 1.25:
        warnings.append("DRY_RUN_SIGNAL_COUNT_NEAR_FLOOR")

    ok = not reason_codes
    score = (
        mean_edge
        + median_edge * 0.5
        + (profit_factor - 1.0) * 50.0
        + win_rate * 0.3
        + oos_edge * 0.5
        + walk_forward_rate * 0.2
        - max_dd_pct * 2.0
        - max(0.0, dominant_action_pct - 55.0) * 1.5
        - top_trade_edge_share_pct * 0.3
    )
    metrics = {
        "rows": len(enriched),
        "signal_count": signal_count,
        "signal_coverage_pct": round(signal_coverage_pct, 6),
        "mean_net_edge_bps": round(mean_edge, 6),
        "median_net_edge_bps": round(median_edge, 6),
        "win_rate_pct": round(win_rate, 6),
        "profit_factor": round(float(profit_factor), 6),
        "max_drawdown_pct": round(max_dd_pct, 6),
        "oos_mean_net_edge_bps": round(oos_edge, 6),
        "walk_forward_positive_rate_pct": round(walk_forward_rate, 6),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "dominant_action_pct": round(dominant_action_pct, 6),
        "top_trade_edge_share_pct": round(top_trade_edge_share_pct, 6),
        "funding_coverage_pct": round(funding_coverage, 6),
        "open_interest_coverage_pct": round(oi_coverage, 6),
        "long_short_coverage_pct": round(long_short_coverage, 6),
        "taker_coverage_pct": round(taker_coverage, 6),
        "round_trip_cost_bps": round(spec.round_trip_cost_bps, 6),
    }
    return DryRunCandidateResult(
        contract_version=FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION,
        decision="PASS" if ok else "BLOCK",
        ok=ok,
        approved_for_research_candidate=ok,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        reload_allowed=False,
        reason_codes=reason_codes,
        warnings=warnings,
        score=round(score, 6),
        spec=asdict(spec),
        metrics=metrics,
        trades=[asdict(trade) for trade in trades],
    )


def build_futures_research_candidate_simulator_report(
    df: pd.DataFrame,
    spec: FuturesResearchCandidateSpec,
    source: str,
    limits: DryRunSimulatorLimits | None = None,
) -> DryRunSimulatorReport:
    candidate = evaluate_dry_run_candidate(df, spec, limits)
    reason_codes = list(candidate.reason_codes)
    if not candidate.ok and "NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED" not in reason_codes:
        reason_codes.insert(0, "NO_DRY_RUN_RESEARCH_CANDIDATE_PASSED")
    recommendation = (
        "Futures dry-run signal simulator passed the research-candidate gate. Treat it only as a research candidate; do not train, reload, paper trade, or enable live trading yet."
        if candidate.ok
        else "No futures dry-run research candidate passed. Do not train, reload, start paper trading, or enable live trading. Revisit the futures hypothesis or robustness inputs."
    )
    return DryRunSimulatorReport(
        contract_version=FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION,
        phase=FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION,
        report_type="futures_research_candidate_dry_run_signal_simulator",
        decision="PASS" if candidate.ok else "BLOCK",
        ok=candidate.ok,
        source=source,
        selected={
            "symbol": spec.symbol,
            "interval": spec.interval,
            "strategy": spec.strategy,
            "mean_net_edge_bps": candidate.metrics["mean_net_edge_bps"],
            "profit_factor": candidate.metrics["profit_factor"],
            "signal_count": candidate.metrics["signal_count"],
        },
        approved_for_research_candidate=candidate.ok,
        approved_for_training_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_allowed=False,
        reload_performed=False,
        config_mutation_performed=False,
        order_actions_performed=False,
        no_post_actions=True,
        observation_only=True,
        reason_codes=reason_codes,
        warnings=list(candidate.warnings),
        recommendation=recommendation,
        candidate=asdict(candidate),
        guardrails={
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
    )


def write_markdown_report(path: str | Path, report: DryRunSimulatorReport) -> None:
    candidate = report.candidate
    metrics = candidate.get("metrics", {})
    trades = candidate.get("trades", [])[:50]
    lines = [
        f"# {FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION} Futures Research Candidate Dry-Run Signal Simulator",
        "",
        f"- contract_version: `{report.contract_version}`",
        f"- decision: **{report.decision}**",
        f"- source: `{report.source}`",
        f"- selected: `{report.selected['symbol']}` `{report.selected['interval']}` `{report.selected['strategy']}`",
        f"- approved_for_research_candidate: `{report.approved_for_research_candidate}`",
        f"- approved_for_training_candidate: `{report.approved_for_training_candidate}`",
        f"- approved_for_paper_candidate: `{report.approved_for_paper_candidate}`",
        f"- approved_for_live_real: `{report.approved_for_live_real}`",
        f"- recommendation: {report.recommendation}",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in report.guardrails.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
    ])
    for key, value in metrics.items():
        lines.append(f"| {key} | `{value}` |")
    lines.extend([
        "",
        "## Decision",
        "",
        f"- reason_codes: `{report.reason_codes}`",
        f"- warnings: `{report.warnings}`",
        "",
        "## First Trades",
        "",
        "| # | entry_time | exit_time | side | net_edge_bps | reason |",
        "|---:|---|---|---|---:|---|",
    ])
    for idx, trade in enumerate(trades, 1):
        lines.append(
            f"| {idx} | {trade.get('entry_time')} | {trade.get('exit_time')} | {trade.get('side')} | {trade.get('net_edge_bps')} | {trade.get('reason')} |"
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool uses public futures market data only and never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate for the next controlled phase; paper/live trading remains blocked.",
    ])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_bundle(report: DryRunSimulatorReport, out_dir: str | Path, timestamp: str | None = None) -> tuple[Path, Path]:
    stamp = timestamp or _utc_now_stamp()
    out = Path(out_dir)
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, asdict(report))
    write_markdown_report(md_path, report)
    return json_path, md_path
