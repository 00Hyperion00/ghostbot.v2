"""4B.4.3.6.6.24M timeframe / symbol / strategy edge exploration.

GET-only public-market-data research tool. It never mutates config, reloads models,
starts paper/live trading, or sends orders.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradebot.timeframe_symbol_strategy_edge_exploration import (
    TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION,
    build_timeframe_symbol_strategy_edge_exploration,
    timeframe_to_minutes,
)

REPORT_PREFIX = "4B436624M_timeframe_symbol_strategy_edge_exploration"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def parse_csv_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in str(value).split(",") if item.strip()]


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str, timeout_sec: float = 20.0) -> pd.DataFrame:
    minutes = timeframe_to_minutes(interval)
    total_candles = max(int((int(days) * 24 * 60) / max(minutes, 1)), 50)
    all_klines: list[list[Any]] = []
    end_time: int | None = None
    while len(all_klines) < total_candles:
        limit = min(1000, total_candles - len(all_klines))
        query = {"symbol": symbol.upper(), "interval": interval, "limit": str(limit)}
        if end_time is not None:
            query["endTime"] = str(end_time)
        url = base_url.rstrip("/") + "/api/v3/klines?" + urllib.parse.urlencode(query)
        with urllib.request.urlopen(url, timeout=float(timeout_sec)) as response:  # noqa: S310 - public Binance HTTPS endpoint supplied by operator
            data = json.loads(response.read().decode("utf-8"))
        if not data:
            break
        all_klines = list(data) + all_klines
        end_time = int(data[0][0]) - 1
        time.sleep(0.12)
    if not all_klines:
        raise RuntimeError(f"No klines returned for {symbol} {interval}")
    rows = all_klines[-total_candles:]
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"])
    return df[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]].astype(float)


def load_datasets(args: argparse.Namespace) -> tuple[dict[tuple[str, str], pd.DataFrame], str]:
    if args.input_csv:
        symbol = str(args.symbols or "LOCAL").split(",")[0].strip().upper() or "LOCAL"
        interval = str(args.intervals or "1m").split(",")[0].strip() or "1m"
        return {(symbol, interval): pd.read_csv(args.input_csv)}, f"csv:{args.input_csv}:{symbol}:{interval}"
    symbols = parse_csv_list(args.symbols, ["ETHUSDT"])
    intervals = parse_csv_list(args.intervals, ["1m", "5m", "15m"])
    datasets: dict[tuple[str, str], pd.DataFrame] = {}
    max_pairs = int(args.max_pairs or 50)
    pair_count = 0
    for symbol in symbols:
        for interval in intervals:
            if pair_count >= max_pairs:
                break
            datasets[(symbol.upper(), interval)] = fetch_klines(symbol, interval, int(args.days), base_url=args.base_url, timeout_sec=float(args.timeout_sec))
            pair_count += 1
        if pair_count >= max_pairs:
            break
    return datasets, f"binance:{','.join(symbols)}:{','.join(intervals)}:{args.days}d"


def write_reports(report: Mapping[str, Any], *, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# 4B.4.3.6.6.24M Timeframe / Symbol / Strategy Edge Exploration",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_symbol: `{report.get('selected_symbol')}`",
        f"- selected_interval: `{report.get('selected_interval')}`",
        f"- selected_strategy: `{report.get('selected_strategy')}`",
        f"- selected_score: `{_fmt(report.get('selected_score'))}`",
        f"- selected_mean_edge_bps: `{_fmt(report.get('selected_mean_edge_bps'))}`",
        f"- selected_win_rate_pct: `{_fmt(report.get('selected_win_rate_pct'))}`",
        f"- selected_signal_coverage_pct: `{_fmt(report.get('selected_signal_coverage_pct'))}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    guard = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    for key in ("observation_only", "get_only_public_market_data", "no_post_actions", "post_requests_allowed", "config_mutation_performed", "order_actions_performed", "reload_performed", "live_real_allowed"):
        lines.append(f"- {key}: `{guard.get(key)}`")
    lines.extend([
        "",
        "## Candidates",
        "",
        "| # | decision | symbol | interval | strategy | score | coverage_pct | mean_edge_bps | median_edge_bps | win_pct | profit_factor | reasons | warnings |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ])
    for idx, item in enumerate(report.get("candidates") or [], start=1):
        if not isinstance(item, Mapping):
            continue
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        strategy = item.get("strategy") if isinstance(item.get("strategy"), Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(idx),
                    str(item.get("decision")),
                    str(item.get("symbol")),
                    str(item.get("interval")),
                    str(strategy.get("name")),
                    _fmt(item.get("score")),
                    _fmt(metrics.get("signal_coverage_pct")),
                    _fmt(metrics.get("mean_net_edge_bps")),
                    _fmt(metrics.get("median_net_edge_bps")),
                    _fmt(metrics.get("win_rate_pct")),
                    _fmt(metrics.get("profit_factor")),
                    f"`{item.get('reason_codes') or []}`",
                    f"`{item.get('warnings') or []}`",
                ]
            )
            + " |"
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool only explores public-market-data edge candidates. It never trains models, reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a research candidate; paper/live trading remains blocked.",
    ])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24M timeframe/symbol/strategy edge exploration")
    parser.add_argument("--symbols", default="ETHUSDT", help="Comma-separated symbols, e.g. ETHUSDT,BTCUSDT,SOLUSDT")
    parser.add_argument("--intervals", default="1m,5m,15m", help="Comma-separated intervals, e.g. 1m,3m,5m,15m")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--cost-bps", type=float, default=16.0)
    parser.add_argument("--max-pairs", type=int, default=50)
    parser.add_argument("--max-combinations", type=int, default=None)
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Operator acknowledgement: observation only; no trading actions.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.review_ok:
        raise SystemExit("--review-ok is required because this is a research/reporting tool")
    datasets, source = load_datasets(args)
    report = build_timeframe_symbol_strategy_edge_exploration(datasets, cost_bps=float(args.cost_bps), max_combinations=args.max_combinations)
    report["source"] = source
    json_path, md_path = write_reports(report, out_dir=args.out_dir)
    print(f"{TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION} timeframe/symbol/strategy edge exploration {report.get('decision')}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected: {report.get('selected_symbol')} {report.get('selected_interval')} {report.get('selected_strategy')}")
    print(f" - selected_mean_edge_bps: {report.get('selected_mean_edge_bps')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0 if report.get("decision") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
