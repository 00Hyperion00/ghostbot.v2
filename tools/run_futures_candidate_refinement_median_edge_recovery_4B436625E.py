from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.futures_candidate_refinement_median_edge_recovery import (  # noqa: E402
    FUTURES_REFINEMENT_CONTRACT_VERSION,
    REPORT_PREFIX,
    FuturesRefinementSpec,
    build_futures_candidate_refinement_report,
    derive_spec_from_report,
    report_to_markdown,
)

FUTURES_DATA_RETENTION_DAYS = 29
FUTURES_DATA_RETENTION_MS = FUTURES_DATA_RETENTION_DAYS * 24 * 60 * 60 * 1000


def utc_ms() -> int:
    return int(time.time() * 1000)


def interval_to_ms(interval: str) -> int:
    unit = interval[-1]
    amount = int(interval[:-1])
    multipliers = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    if unit not in multipliers:
        raise ValueError(f"unsupported interval: {interval}")
    return amount * multipliers[unit]


def clamp_futures_data_start_ms(start_ms: int, end_ms: int) -> int:
    return max(int(start_ms), int(end_ms) - FUTURES_DATA_RETENTION_MS)


def http_get_json(base_url: str, path: str, params: dict[str, Any], timeout_sec: float = 15.0) -> Any:
    query = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"User-Agent": "tradebot-25E-median-edge-recovery/1.0"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_sec) as response:  # nosec B310 - public Binance GET only
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body_suffix = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
            body_suffix = f" body={body[:240]}"
        except Exception:
            pass
        raise RuntimeError(f"GET request failed for {path}: HTTP Error {exc.code}:{body_suffix}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET request failed for {path}: {exc}") from exc


def safe_fetch_futures_data_series(
    base_url: str,
    path: str,
    symbol: str,
    period: str,
    start_ms: int,
    end_ms: int,
    timeout_sec: float,
) -> pd.DataFrame:
    safe_start = clamp_futures_data_start_ms(start_ms, end_ms)
    try:
        payload = http_get_json(
            base_url,
            path,
            {"symbol": symbol, "period": period, "startTime": safe_start, "endTime": end_ms, "limit": 500},
            timeout_sec=timeout_sec,
        )
    except Exception as exc:
        print(f"WARNING: optional futures data endpoint failed for {path} {symbol} {period}: {exc}", file=sys.stderr)
        return pd.DataFrame()
    if not isinstance(payload, list):
        return pd.DataFrame()
    return pd.DataFrame(payload)


def fetch_klines(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = utc_ms()
    start_ms = end_ms - int(days) * 24 * 60 * 60 * 1000
    step_ms = interval_to_ms(interval)
    rows: list[list[Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": 1500},
            timeout_sec=timeout_sec,
        )
        if not isinstance(payload, list) or not payload:
            break
        rows.extend(payload)
        next_cursor = int(payload[-1][0]) + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < 1500:
            break
    if not rows:
        raise RuntimeError(f"No futures kline data returned for {symbol} {interval}")
    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trade_count",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )
    return df


def fetch_funding(base_url: str, symbol: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = utc_ms()
    start_ms = end_ms - int(days) * 24 * 60 * 60 * 1000
    payload = http_get_json(
        base_url,
        "/fapi/v1/fundingRate",
        {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000},
        timeout_sec=timeout_sec,
    )
    if not isinstance(payload, list):
        return pd.DataFrame()
    return pd.DataFrame(payload)


def _merge_asof(base: pd.DataFrame, other: pd.DataFrame, time_col: str, rename: dict[str, str]) -> pd.DataFrame:
    if other.empty or time_col not in other.columns:
        return base
    rhs = other.copy()
    rhs[time_col] = pd.to_numeric(rhs[time_col], errors="coerce")
    rhs = rhs.dropna(subset=[time_col]).sort_values(time_col)
    rhs = rhs.rename(columns=rename)
    keep_cols = [time_col] + [v for v in rename.values() if v in rhs.columns]
    rhs = rhs[keep_cols]
    return pd.merge_asof(base.sort_values("open_time"), rhs, left_on="open_time", right_on=time_col, direction="backward").drop(columns=[time_col], errors="ignore")


def fetch_futures_dataset(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = utc_ms()
    start_ms = end_ms - int(days) * 24 * 60 * 60 * 1000
    klines = fetch_klines(base_url, symbol, interval, days, timeout_sec)
    klines["open_time"] = pd.to_numeric(klines["open_time"], errors="coerce")
    df = klines.sort_values("open_time")

    funding = fetch_funding(base_url, symbol, min(days, FUTURES_DATA_RETENTION_DAYS), timeout_sec)
    if not funding.empty:
        df = _merge_asof(df, funding, "fundingTime", {"fundingRate": "fundingRate"})

    period = interval if interval in {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"} else "1h"
    oi = safe_fetch_futures_data_series(base_url, "/futures/data/openInterestHist", symbol, period, start_ms, end_ms, timeout_sec)
    if not oi.empty:
        df = _merge_asof(df, oi, "timestamp", {"sumOpenInterest": "sumOpenInterest"})
    long_short = safe_fetch_futures_data_series(base_url, "/futures/data/globalLongShortAccountRatio", symbol, period, start_ms, end_ms, timeout_sec)
    if not long_short.empty:
        df = _merge_asof(df, long_short, "timestamp", {"longShortRatio": "longShortRatio"})
    taker = safe_fetch_futures_data_series(base_url, "/futures/data/takerlongshortRatio", symbol, period, start_ms, end_ms, timeout_sec)
    if not taker.empty:
        df = _merge_asof(df, taker, "timestamp", {"buySellRatio": "buySellRatio", "buyVol": "buyVol", "sellVol": "sellVol"})
    return df


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def derive_spec(args: argparse.Namespace) -> FuturesRefinementSpec:
    if args.spec_json:
        data = load_json(args.spec_json)
        spec_data = data.get("candidate_spec", data)
        return FuturesRefinementSpec(
            symbol=str(spec_data.get("symbol", "BTCUSDT")),
            interval=str(spec_data.get("interval", "4h")),
            strategy=str(spec_data.get("strategy", "funding_trend_exhaustion")),
            horizon_bars=int(spec_data.get("horizon_bars", 1)),
            round_trip_cost_bps=float(spec_data.get("round_trip_cost_bps", 16.0)),
            min_edge_bps=float(spec_data.get("min_edge_bps", 0.0)),
        )
    if args.input_json:
        return derive_spec_from_report(load_json(args.input_json))
    return FuturesRefinementSpec(symbol=args.symbol, interval=args.interval, strategy=args.strategy)


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25E futures candidate refinement / median edge recovery")
    parser.add_argument("--input-json", default=None, help="25D/25C/25B report JSON to derive selected futures candidate")
    parser.add_argument("--spec-json", default=None, help="Explicit futures research candidate spec JSON")
    parser.add_argument("--input-csv", default=None, help="Local futures feature CSV for deterministic/offline evaluation")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--strategy", default="funding_trend_exhaustion")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://fapi.binance.com")
    parser.add_argument("--timeout-sec", type=float, default=15.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this tool cannot approve paper/live trading")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. Backtest/research PASS is not paper/live permission.", file=sys.stderr)
        return 2
    spec = derive_spec(args)
    if args.input_csv:
        csv_path = Path(args.input_csv)
        if not csv_path.exists():
            raise FileNotFoundError(f"Input CSV not found: {csv_path}")
        df = pd.read_csv(csv_path)
        source = f"csv:{csv_path}:{spec.symbol}:{spec.interval}:{spec.strategy}"
    else:
        df = fetch_futures_dataset(args.base_url, spec.symbol, spec.interval, args.days, args.timeout_sec)
        source = f"binance-futures:{spec.symbol}:{spec.interval}:{args.days}d:{spec.strategy}"
    report = build_futures_candidate_refinement_report(df, spec, source=source)
    json_path, md_path = write_report(report, Path(args.out_dir))
    print(f"{FUTURES_REFINEMENT_CONTRACT_VERSION} futures median-edge refinement {report['decision']}")
    print(f" - selected: {spec.symbol} {spec.interval} {spec.strategy}")
    print(f" - selected_filter: {report.get('selected_filter')}")
    print(f" - signal_count: {report.get('selected_signal_count')}")
    print(f" - mean_net_edge_bps: {report.get('selected_mean_net_edge_bps')}")
    print(f" - median_net_edge_bps: {report.get('selected_median_net_edge_bps')}")
    print(f" - profit_factor: {report.get('selected_profit_factor')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
