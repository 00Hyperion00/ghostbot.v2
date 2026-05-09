from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp003_regime_strategy_exploration import (  # noqa: E402
    HYP003_EXPLORATION_CONTRACT_VERSION,
    REPORT_PREFIX,
    build_hyp003_regime_strategy_exploration_report,
    load_json,
    report_to_markdown,
    write_json,
)


def interval_to_ms(interval: str) -> int:
    unit = interval[-1]
    value = int(interval[:-1])
    factors = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    if unit not in factors:
        raise ValueError(f"unsupported interval: {interval}")
    return value * factors[unit]


def http_get_json(base_url: str, path: str, params: dict[str, Any], timeout_sec: float) -> Any:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"User-Agent": f"tradebot-{HYP003_EXPLORATION_CONTRACT_VERSION}"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_sec) as response:  # nosec B310 - public market-data GET only
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body_suffix = ""
        try:
            body_suffix = " body=" + exc.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            pass
        raise RuntimeError(f"GET {path} failed: HTTP {exc.code}{body_suffix}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {path} failed: {exc}") from exc


def fetch_spot_klines(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(days) * 86_400_000
    step_ms = interval_to_ms(interval)
    rows: list[list[Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = http_get_json(
            base_url,
            "/api/v3/klines",
            {"symbol": symbol, "interval": interval, "startTime": cursor, "endTime": end_ms, "limit": 1000},
            timeout_sec,
        )
        if not isinstance(payload, list) or not payload:
            break
        rows.extend(payload)
        next_cursor = int(payload[-1][0]) + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(payload) < 1000:
            break
        time.sleep(0.05)
    if not rows:
        raise RuntimeError(f"No kline data returned for {symbol} {interval}")
    return pd.DataFrame(
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


def parse_csv_inputs(items: list[str]) -> dict[tuple[str, str], pd.DataFrame]:
    datasets: dict[tuple[str, str], pd.DataFrame] = {}
    for item in items:
        # Format: SYMBOL:INTERVAL:PATH
        parts = item.split(":", 2)
        if len(parts) != 3:
            raise ValueError("--input-csv format must be SYMBOL:INTERVAL:PATH")
        symbol, interval, path = parts[0].upper(), parts[1], parts[2]
        datasets[(symbol, interval)] = pd.read_csv(path)
    return datasets


def write_report_bundle(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, report)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25J HYP-003 regime-specific strategy family exploration gate")
    parser.add_argument("--input-json", action="append", default=[], help="25I report/proposed registry snapshot proving HYP-003 was selected. Can be repeated.")
    parser.add_argument("--input-csv", action="append", default=[], help="Offline CSV in SYMBOL:INTERVAL:PATH format. Can be repeated.")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--intervals", default="1h,4h")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement: research-only, no paper/live/training/reload/orders.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This gate is research-only and never approves paper/live trading.", file=sys.stderr)
        return 2
    input_reports = [load_json(path) for path in args.input_json]
    if args.input_csv:
        datasets = parse_csv_inputs(args.input_csv)
        source = "csv:" + ",".join(args.input_csv)
    else:
        datasets: dict[tuple[str, str], pd.DataFrame] = {}
        symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()]
        intervals = [item.strip() for item in args.intervals.split(",") if item.strip()]
        for symbol in symbols:
            for interval in intervals:
                datasets[(symbol, interval)] = fetch_spot_klines(args.base_url, symbol, interval, args.days, args.timeout_sec)
        source = f"binance-spot:{args.symbols}:{args.intervals}:{args.days}d"
    report = build_hyp003_regime_strategy_exploration_report(datasets, input_reports=input_reports, source=source)
    json_path, md_path = write_report_bundle(report, Path(args.out_dir))
    selected = report.get("selected_candidate") or {}
    metrics = selected.get("metrics", {}) if isinstance(selected, dict) else {}
    print(f"{HYP003_EXPLORATION_CONTRACT_VERSION} HYP-003 regime strategy exploration {report['decision']}")
    print(f" - hypothesis_id: {report.get('hypothesis_id')}")
    print(f" - candidate_count: {report.get('candidate_count')}")
    print(f" - passed_candidate_count: {report.get('passed_candidate_count')}")
    print(f" - selected: {selected.get('symbol')} {selected.get('interval')} {selected.get('strategy_family')} {selected.get('regime')}")
    print(f" - selected_signal_count: {metrics.get('signal_count')}")
    print(f" - selected_mean_net_edge_bps: {metrics.get('mean_net_edge_bps')}")
    print(f" - selected_median_net_edge_bps: {metrics.get('median_net_edge_bps')}")
    print(f" - selected_profit_factor: {metrics.get('profit_factor')}")
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
