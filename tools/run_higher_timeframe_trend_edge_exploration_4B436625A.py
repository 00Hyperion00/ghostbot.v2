from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tradebot.higher_timeframe_trend_edge_exploration import (
    HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION,
    build_timeframe_symbol_strategy_edge_exploration,
    render_timeframe_symbol_strategy_edge_markdown,
)

REPORT_PREFIX = "4B436625A_higher_timeframe_trend_edge_exploration"
KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]

INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 3 * 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "2h": 2 * 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "6h": 6 * 60 * 60_000,
    "8h": 8 * 60 * 60_000,
    "12h": 12 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _fetch_binance_klines(
    *,
    symbol: str,
    interval: str,
    days: int,
    base_url: str,
    timeout_sec: int,
) -> pd.DataFrame:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval for fetch: {interval}")
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - int(days) * 24 * 60 * 60 * 1000
    end_ms = now_ms
    step_ms = INTERVAL_MS[interval]
    rows: list[list[Any]] = []
    cursor = start_ms

    while cursor < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": interval,
                "limit": 1000,
                "startTime": cursor,
                "endTime": end_ms,
            }
        )
        url = f"{base_url.rstrip('/')}/api/v3/klines?{params}"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:  # nosec - user supplied public API URL
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        rows.extend(payload)
        last_open = int(payload[-1][0])
        next_cursor = last_open + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < 1000:
            break
        time.sleep(0.05)

    df = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    if df.empty:
        raise RuntimeError(f"No klines returned for {symbol} {interval}")
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


def load_datasets(args: argparse.Namespace) -> tuple[dict[tuple[str, str], pd.DataFrame], str]:
    symbols = _split_csv(args.symbols)
    intervals = _split_csv(args.intervals)
    if not symbols:
        raise ValueError("At least one symbol is required")
    if not intervals:
        raise ValueError("At least one interval is required")

    if args.input_csv:
        csv_path = Path(args.input_csv)
        if not csv_path.exists():
            raise FileNotFoundError(f"Input CSV not found: {csv_path}")
        symbol = symbols[0]
        interval = intervals[0]
        return {(symbol, interval): pd.read_csv(csv_path)}, f"csv:{csv_path}:{symbol}:{interval}"

    datasets: dict[tuple[str, str], pd.DataFrame] = {}
    for symbol in symbols:
        for interval in intervals:
            datasets[(symbol, interval)] = _fetch_binance_klines(
                symbol=symbol,
                interval=interval,
                days=args.days,
                base_url=args.base_url,
                timeout_sec=args.timeout_sec,
            )
    return datasets, f"binance:{','.join(symbols)}:{','.join(intervals)}:{args.days}d"


def write_reports(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_timeframe_symbol_strategy_edge_markdown(report), encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25A higher timeframe trend edge exploration")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    parser.add_argument("--intervals", default="30m,1h,4h")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-csv", default="")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--timeout-sec", type=int, default=20)
    parser.add_argument("--cost-bps", type=float, default=16.0)
    parser.add_argument("--review-ok", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.review_ok:
        parser.error("--review-ok is required because this tool creates research reports and must be run intentionally")

    datasets, source = load_datasets(args)
    report = build_timeframe_symbol_strategy_edge_exploration(
        datasets,
        source=source,
        cost_bps=float(args.cost_bps),
    )
    json_path, md_path = write_reports(report, Path(args.out_dir))

    selected = report.get("selected") or {}
    print(f"{HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION} higher timeframe trend edge exploration {report['decision']}")
    print(f" - candidates: {report['candidate_count']}")
    print(f" - approved_for_research_candidate: {report['approved_for_research_candidate']}")
    print(f" - approved_for_training_candidate: {report['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f" - selected: {selected.get('symbol')} {selected.get('interval')} {selected.get('strategy')}")
    print(f" - selected_mean_net_edge_bps: {selected.get('mean_net_edge_bps')}")
    print(f" - selected_profit_factor: {selected.get('profit_factor')}")
    print(f" - recommendation: {report['recommendation']}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
