from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from tradebot.futures_funding_open_interest_edge_exploration import (
    FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION,
    build_futures_funding_open_interest_edge_exploration,
    write_report_files,
)

PERIOD_MS = {
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "2h": 2 * 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "6h": 6 * 60 * 60_000,
    "12h": 12 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

KLINE_INTERVAL_MS = {
    "1m": 60_000,
    "3m": 3 * 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "2h": 2 * 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

FUTURES_DATA_RETENTION_DAYS = 29
FUTURES_DATA_RETENTION_MS = FUTURES_DATA_RETENTION_DAYS * 24 * 60 * 60_000
FUTURES_DATA_LIMIT = 500
FUTURES_DATA_ENDPOINTS = {
    "/futures/data/openInterestHist",
    "/futures/data/globalLongShortAccountRatio",
    "/futures/data/takerlongshortRatio",
}


def http_get_json(base_url: str, path: str, params: dict[str, Any], *, timeout_sec: int, retries: int = 2) -> Any:
    url = f"{base_url.rstrip('/')}{path}?{urlencode(params)}"
    last_error: Exception | None = None
    last_body = ""
    for attempt in range(retries + 1):
        try:
            request = Request(url, method="GET", headers={"User-Agent": "tradebot-25B-research"})
            with urlopen(request, timeout=timeout_sec) as response:  # noqa: S310 - public configured endpoint
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover - network dependent
            last_error = exc
            try:
                last_body = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                last_body = ""
            if exc.code in {400, 404}:
                break
            if attempt < retries:
                time.sleep(0.4 + 0.3 * attempt)
        except (URLError, TimeoutError, Exception) as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < retries:
                time.sleep(0.4 + 0.3 * attempt)
    body_suffix = f" body={last_body}" if last_body else ""
    raise RuntimeError(f"GET request failed for {path}: {last_error}{body_suffix}")


def clamp_futures_data_start_ms(start_ms: int, end_ms: int) -> int:
    # Binance /futures/data series expose only the latest 30 days/1 month.
    # Use a 29-day safety window to avoid boundary 400s from clock drift.
    return max(start_ms, end_ms - FUTURES_DATA_RETENTION_MS)


def safe_fetch_futures_data_series(
    base_url: str,
    endpoint: str,
    symbol: str,
    period: str,
    start_ms: int,
    end_ms: int,
    timeout_sec: int,
) -> pd.DataFrame:
    try:
        return fetch_futures_data_series(base_url, endpoint, symbol, period, start_ms, end_ms, timeout_sec)
    except RuntimeError as exc:  # pragma: no cover - network dependent
        print(
            f"WARN: optional futures data endpoint failed and will be treated as missing: "
            f"{endpoint} {symbol} {period}: {exc}",
            file=sys.stderr,
        )
        return pd.DataFrame()


def fetch_klines(base_url: str, symbol: str, interval: str, start_ms: int, end_ms: int, timeout_sec: int) -> pd.DataFrame:
    interval_ms = KLINE_INTERVAL_MS.get(interval)
    if interval_ms is None:
        raise ValueError(f"Unsupported kline interval: {interval}")
    rows: list[list[Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": 1500},
            timeout_sec=timeout_sec,
        )
        if not payload:
            break
        rows.extend(payload)
        last_open = int(payload[-1][0])
        cursor = last_open + interval_ms
        if len(payload) < 1500:
            break
    if not rows:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )
    return frame


def fetch_funding_rates(base_url: str, symbol: str, start_ms: int, end_ms: int, timeout_sec: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/fapi/v1/fundingRate",
            {"symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000},
            timeout_sec=timeout_sec,
        )
        if not payload:
            break
        rows.extend(payload)
        last_time = int(payload[-1]["fundingTime"])
        cursor = last_time + 1
        if len(payload) < 1000:
            break
    if not rows:
        return pd.DataFrame(columns=["timestamp", "funding_rate"])
    frame = pd.DataFrame(rows)
    return frame.rename(columns={"fundingTime": "timestamp", "fundingRate": "funding_rate"})[["timestamp", "funding_rate"]]


def fetch_futures_data_series(
    base_url: str,
    endpoint: str,
    symbol: str,
    period: str,
    start_ms: int,
    end_ms: int,
    timeout_sec: int,
) -> pd.DataFrame:
    period_ms = PERIOD_MS.get(period)
    if period_ms is None:
        raise ValueError(f"Unsupported futures-data period: {period}")

    # /futures/data endpoints are bounded to the latest 30 days/1 month.
    # Clamp the start to a conservative 29-day window. Older kline rows remain
    # valid; optional futures metrics simply become unavailable before the
    # retention boundary and are handled by metric coverage gates.
    if endpoint in FUTURES_DATA_ENDPOINTS:
        start_ms = clamp_futures_data_start_ms(start_ms, end_ms)

    rows: list[dict[str, Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        chunk_end = min(end_ms, cursor + period_ms * (FUTURES_DATA_LIMIT - 1))
        payload = http_get_json(
            base_url,
            endpoint,
            {
                "symbol": symbol,
                "period": period,
                "startTime": cursor,
                "endTime": chunk_end,
                "limit": FUTURES_DATA_LIMIT,
            },
            timeout_sec=timeout_sec,
        )
        if not payload:
            cursor = chunk_end + period_ms
            continue
        rows.extend(payload)
        last_time = int(payload[-1].get("timestamp", cursor))
        next_cursor = max(cursor + period_ms, last_time + period_ms)
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < FUTURES_DATA_LIMIT and cursor >= end_ms:
            break
        if len(rows) > 50_000:
            break
    return pd.DataFrame(rows)


def merge_metric_asof(base: pd.DataFrame, metric: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if metric.empty:
        for column in columns:
            if column not in base.columns:
                base[column] = pd.NA
        return base
    left = base.copy()
    right = metric.copy()
    left["timestamp_dt"] = pd.to_datetime(left["open_time"], unit="ms", utc=True, errors="coerce")
    right["timestamp_dt"] = pd.to_datetime(right["timestamp"], unit="ms", utc=True, errors="coerce")
    right = right.sort_values("timestamp_dt")
    left = left.sort_values("timestamp_dt")
    keep = ["timestamp_dt"] + [column for column in columns if column in right.columns]
    merged = pd.merge_asof(left, right[keep], on="timestamp_dt", direction="backward")
    return merged.drop(columns=["timestamp_dt"])


def fetch_futures_dataset(
    base_url: str,
    symbol: str,
    interval: str,
    days: int,
    timeout_sec: int,
) -> pd.DataFrame:
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    period = interval if interval in PERIOD_MS else "1h"
    klines = fetch_klines(base_url, symbol, interval, start_ms, end_ms, timeout_sec)
    if klines.empty:
        return klines

    funding = fetch_funding_rates(base_url, symbol, start_ms, end_ms, timeout_sec)
    klines = merge_metric_asof(klines, funding, ["funding_rate"])

    open_interest = safe_fetch_futures_data_series(base_url, "/futures/data/openInterestHist", symbol, period, start_ms, end_ms, timeout_sec)
    open_interest = open_interest.rename(columns={"sumOpenInterest": "sum_open_interest", "sumOpenInterestValue": "sum_open_interest_value"})
    klines = merge_metric_asof(klines, open_interest, ["sum_open_interest", "sum_open_interest_value"])

    long_short = safe_fetch_futures_data_series(base_url, "/futures/data/globalLongShortAccountRatio", symbol, period, start_ms, end_ms, timeout_sec)
    long_short = long_short.rename(columns={"longShortRatio": "long_short_ratio", "longAccount": "long_account", "shortAccount": "short_account"})
    klines = merge_metric_asof(klines, long_short, ["long_short_ratio", "long_account", "short_account"])

    taker = safe_fetch_futures_data_series(base_url, "/futures/data/takerlongshortRatio", symbol, period, start_ms, end_ms, timeout_sec)
    taker = taker.rename(columns={"buySellRatio": "taker_buy_sell_ratio", "buyVol": "taker_buy_volume", "sellVol": "taker_sell_volume"})
    klines = merge_metric_asof(klines, taker, ["taker_buy_sell_ratio", "taker_buy_volume", "taker_sell_volume"])
    return klines


def load_datasets(args: argparse.Namespace) -> tuple[dict[tuple[str, str], pd.DataFrame], str]:
    symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()]
    intervals = [item.strip() for item in args.intervals.split(",") if item.strip()]
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
            datasets[(symbol, interval)] = fetch_futures_dataset(args.base_url, symbol, interval, args.days, args.timeout_sec)
    return datasets, f"binance-futures:{','.join(symbols)}:{','.join(intervals)}:{args.days}d"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25B futures funding/open-interest edge exploration")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    parser.add_argument("--intervals", default="30m,1h,4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://fapi.binance.com")
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--timeout-sec", type=int, default=20)
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required because this is a research gate tool.", file=sys.stderr)
        return 2
    datasets, source = load_datasets(args)
    report = build_futures_funding_open_interest_edge_exploration(datasets, source=source)
    json_path, md_path = write_report_files(report, args.out_dir)

    selected = report.get("selected") or {}
    print(f"{FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION} futures funding/open-interest edge exploration {report['decision']}")
    print(f" - candidates: {report['candidate_count']}")
    print(f" - approved_for_research_candidate: {report['approved_for_research_candidate']}")
    print(f" - approved_for_training_candidate: {report['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    if selected:
        print(f" - selected: {selected.get('symbol')} {selected.get('interval')} {selected.get('strategy')}")
        print(f" - selected_mean_net_edge_bps: {selected.get('mean_net_edge_bps')}")
        print(f" - selected_profit_factor: {selected.get('profit_factor')}")
    print(f" - recommendation: {report['recommendation']}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
