from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from tradebot.futures_research_candidate_simulator import (
    FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION,
    FuturesResearchCandidateSpec,
    build_candidate_spec_from_robustness_report,
    build_futures_research_candidate_simulator_report,
    load_json,
    normalize_market_dataframe,
    write_json,
    write_report_bundle,
)

FUTURES_DATA_RETENTION_DAYS = 29
FUTURES_DATA_RETENTION_MS = FUTURES_DATA_RETENTION_DAYS * 24 * 60 * 60 * 1000


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _interval_to_ms(interval: str) -> int:
    unit = interval[-1]
    value = int(interval[:-1])
    if unit == "m":
        return value * 60_000
    if unit == "h":
        return value * 3_600_000
    if unit == "d":
        return value * 86_400_000
    raise ValueError(f"Unsupported interval: {interval}")


def _interval_to_period(interval: str) -> str:
    if interval in {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}:
        return interval
    return "4h" if interval.endswith("h") else "1h"


def http_get_json(base_url: str, path: str, params: dict[str, Any], timeout_sec: float) -> Any:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"User-Agent": f"tradebot-{FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION}"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            body = ""
        raise RuntimeError(f"GET request failed for {path}: HTTP Error {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET request failed for {path}: {exc}") from exc


def fetch_klines(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = _now_ms()
    start_ms = end_ms - int(days * 86_400_000)
    step_ms = _interval_to_ms(interval)
    rows: list[list[Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": 1500},
            timeout_sec,
        )
        if not payload:
            break
        rows.extend(payload)
        last_open = int(payload[-1][0])
        next_cursor = last_open + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < 1500:
            break
        time.sleep(0.05)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "timestamp": [row[0] for row in rows],
            "open": [row[1] for row in rows],
            "high": [row[2] for row in rows],
            "low": [row[3] for row in rows],
            "close": [row[4] for row in rows],
            "volume": [row[5] for row in rows],
        }
    )


def fetch_funding(base_url: str, symbol: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = _now_ms()
    start_ms = end_ms - int(days * 86_400_000)
    payload = http_get_json(
        base_url,
        "/fapi/v1/fundingRate",
        {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000},
        timeout_sec,
    )
    if not payload:
        return pd.DataFrame(columns=["timestamp", "fundingRate"])
    return pd.DataFrame({"timestamp": [row.get("fundingTime") for row in payload], "fundingRate": [row.get("fundingRate") for row in payload]})


def clamp_futures_data_start_ms(start_ms: int, end_ms: int) -> int:
    return max(start_ms, end_ms - FUTURES_DATA_RETENTION_MS)


def safe_fetch_futures_data_series(base_url: str, path: str, symbol: str, period: str, start_ms: int, end_ms: int, timeout_sec: float) -> pd.DataFrame:
    clamped_start = clamp_futures_data_start_ms(start_ms, end_ms)
    try:
        payload = http_get_json(
            base_url,
            path,
            {"symbol": symbol, "period": period, "startTime": clamped_start, "endTime": end_ms, "limit": 500},
            timeout_sec,
        )
    except RuntimeError as exc:
        print(f"WARNING optional futures data endpoint failed: {path} {symbol} {period}: {exc}", file=sys.stderr)
        return pd.DataFrame()
    if not payload:
        return pd.DataFrame()
    frame = pd.DataFrame(payload)
    if "timestamp" not in frame.columns:
        return pd.DataFrame()
    return frame


def _asof_merge(left: pd.DataFrame, right: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if right.empty:
        for column in columns:
            if column not in left.columns:
                left[column] = pd.NA
        return left
    r = right.copy()
    r["timestamp"] = pd.to_datetime(pd.to_numeric(r["timestamp"], errors="coerce"), unit="ms", utc=True, errors="coerce")
    for column in columns:
        if column in r.columns:
            r[column] = pd.to_numeric(r[column], errors="coerce")
    r = r[["timestamp"] + [c for c in columns if c in r.columns]].dropna(subset=["timestamp"]).sort_values("timestamp")
    return pd.merge_asof(left.sort_values("timestamp"), r, on="timestamp", direction="backward")


def fetch_futures_dataset(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = _now_ms()
    start_ms = end_ms - int(days * 86_400_000)
    period = _interval_to_period(interval)
    klines = normalize_market_dataframe(fetch_klines(base_url, symbol, interval, days, timeout_sec))
    funding = fetch_funding(base_url, symbol, days, timeout_sec)
    oi = safe_fetch_futures_data_series(base_url, "/futures/data/openInterestHist", symbol, period, start_ms, end_ms, timeout_sec)
    long_short = safe_fetch_futures_data_series(base_url, "/futures/data/globalLongShortAccountRatio", symbol, period, start_ms, end_ms, timeout_sec)
    taker = safe_fetch_futures_data_series(base_url, "/futures/data/takerlongshortRatio", symbol, period, start_ms, end_ms, timeout_sec)

    if not funding.empty:
        funding = funding.rename(columns={"fundingTime": "timestamp"})
        funding["timestamp"] = pd.to_datetime(pd.to_numeric(funding["timestamp"], errors="coerce"), unit="ms", utc=True, errors="coerce")
        funding["fundingRate"] = pd.to_numeric(funding["fundingRate"], errors="coerce")
        klines = pd.merge_asof(klines.sort_values("timestamp"), funding[["timestamp", "fundingRate"]].dropna().sort_values("timestamp"), on="timestamp", direction="backward")
    else:
        klines["fundingRate"] = 0.0
    if not oi.empty and "sumOpenInterest" in oi.columns:
        klines = _asof_merge(klines, oi, ["sumOpenInterest"])
    else:
        klines["sumOpenInterest"] = pd.NA
    if not long_short.empty and "longShortRatio" in long_short.columns:
        klines = _asof_merge(klines, long_short, ["longShortRatio"])
    else:
        klines["longShortRatio"] = pd.NA
    if not taker.empty:
        taker = taker.copy()
        if "buySellRatio" not in taker.columns:
            if "buyVol" in taker.columns and "sellVol" in taker.columns:
                taker["buySellRatio"] = pd.to_numeric(taker["buyVol"], errors="coerce") / pd.to_numeric(taker["sellVol"], errors="coerce").replace(0, pd.NA)
        klines = _asof_merge(klines, taker, ["buySellRatio"])
    else:
        klines["buySellRatio"] = pd.NA
    return klines


def load_spec(args: argparse.Namespace) -> FuturesResearchCandidateSpec:
    if args.spec_json:
        raw = json.loads(Path(args.spec_json).read_text(encoding="utf-8"))
        return FuturesResearchCandidateSpec(**{key: value for key, value in raw.items() if key in FuturesResearchCandidateSpec.__dataclass_fields__})
    if args.input_json:
        return build_candidate_spec_from_robustness_report(load_json(args.input_json))
    return FuturesResearchCandidateSpec(symbol=args.symbol, interval=args.interval, strategy=args.strategy)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25D futures research candidate dry-run signal simulator")
    parser.add_argument("--input-json", default=None, help="25C robustness report JSON used to build candidate spec")
    parser.add_argument("--spec-json", default=None, help="Explicit candidate spec JSON")
    parser.add_argument("--input-csv", default=None, help="Local OHLCV/futures-metric CSV")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--strategy", default="funding_trend_exhaustion")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://fapi.binance.com")
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--write-spec", action="store_true")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this does not authorize paper/live trading")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. Backtest/dry-run PASS is not paper/live permission.", file=sys.stderr)
        return 2
    spec = load_spec(args)
    if args.input_csv:
        csv_path = Path(args.input_csv)
        if not csv_path.exists():
            raise FileNotFoundError(f"Input CSV not found: {csv_path}")
        dataset = pd.read_csv(csv_path)
        source = f"csv:{csv_path}:{spec.symbol}:{spec.interval}"
    else:
        dataset = fetch_futures_dataset(args.base_url, spec.symbol, spec.interval, args.days, args.timeout_sec)
        source = f"binance-futures:{spec.symbol}:{spec.interval}:{args.days}d"
    report = build_futures_research_candidate_simulator_report(dataset, spec, source)
    out_dir = Path(args.out_dir)
    json_path, md_path = write_report_bundle(report, out_dir)
    if args.write_spec:
        spec_path = out_dir / f"4B436625D_futures_research_candidate_spec_{spec.symbol}_{spec.interval}_{spec.strategy}.json"
        write_json(spec_path, spec.__dict__)
        print(f"spec_json: {spec_path}")
    metrics = report.candidate.get("metrics", {})
    print(f"{FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION} futures dry-run signal simulator {report.decision}")
    print(f" - selected: {spec.symbol} {spec.interval} {spec.strategy}")
    print(f" - signal_count: {metrics.get('signal_count', 0)}")
    print(f" - mean_net_edge_bps: {metrics.get('mean_net_edge_bps', 0)}")
    print(f" - median_net_edge_bps: {metrics.get('median_net_edge_bps', 0)}")
    print(f" - profit_factor: {metrics.get('profit_factor', 0)}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - reason_codes: {report.reason_codes}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
