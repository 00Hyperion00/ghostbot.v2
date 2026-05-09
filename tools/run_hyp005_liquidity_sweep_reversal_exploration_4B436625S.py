from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_liquidity_sweep_reversal_exploration import (  # noqa: E402
    HYP005_EXPLORATION_CONTRACT_VERSION,
    REPORT_PREFIX,
    build_hyp005_liquidity_sweep_reversal_exploration_report,
    load_json,
    report_to_markdown,
    write_json,
)


def interval_to_ms(interval: str) -> int:
    unit = interval[-1]
    amount = int(interval[:-1])
    mapping = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    if unit not in mapping:
        raise ValueError(f"unsupported interval: {interval}")
    return amount * mapping[unit]


def http_get_json(base_url: str, path: str, params: dict[str, Any], timeout_sec: float) -> Any:
    query = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base_url.rstrip('/')}{path}?{query}" if query else f"{base_url.rstrip('/')}{path}"
    request = Request(url, headers={"User-Agent": "tradebot-25S-hyp005-research/1.0"}, method="GET")
    with urlopen(request, timeout=timeout_sec) as response:  # nosec B310 - public market data GET only
        return json.loads(response.read().decode("utf-8"))


def fetch_spot_klines(base_url: str, symbol: str, interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    step_ms = interval_to_ms(interval)
    cursor = start_ms
    rows: list[list[Any]] = []
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
    if not rows:
        raise RuntimeError(f"No kline data returned for {symbol} {interval}")
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
    df["symbol"] = symbol.upper()
    return df[["symbol", "open_time", "open", "high", "low", "close", "volume"]]


def fetch_multi_symbol_dataset(base_url: str, symbols: list[str], interval: str, days: int, timeout_sec: float) -> pd.DataFrame:
    frames = [fetch_spot_klines(base_url, symbol.upper(), interval, days, timeout_sec) for symbol in symbols]
    return pd.concat(frames, ignore_index=True)


def latest_25r_report(reports_dir: Path) -> Path | None:
    matches = sorted(reports_dir.glob("4B436625R_research_backlog_after_hyp004_closure_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25S HYP-005 liquidity sweep reversal exploration gate")
    parser.add_argument("--input-json", default=None, help="25R backlog advancement report selecting HYP-005.")
    parser.add_argument("--input-csv", default=None, help="Offline CSV with symbol/open_time/open/high/low/close columns.")
    parser.add_argument("--reports-dir", default="reports", help="Directory used to discover latest 25R report if --input-json is omitted.")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT", help="Comma-separated symbols.")
    parser.add_argument("--interval", default="4h", help="Single interval for sweep detection.")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=float, default=15.0)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is research-only and no orders/reload/config mutation are performed.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. HYP-005 exploration is research-only and cannot approve paper/live trading.", file=sys.stderr)
        return 2
    input_json = Path(args.input_json) if args.input_json else latest_25r_report(Path(args.reports_dir))
    selection_report = load_json(input_json) if input_json and input_json.exists() else None
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("ERROR: at least one symbol is required for HYP-005 sweep exploration", file=sys.stderr)
        return 2
    if args.input_csv:
        market_df = pd.read_csv(args.input_csv)
        source = f"csv:{args.input_csv}"
    else:
        market_df = fetch_multi_symbol_dataset(args.base_url, symbols, args.interval, args.days, args.timeout_sec)
        source = f"binance-spot:{','.join(symbols)}:{args.interval}:{args.days}d"
    report = build_hyp005_liquidity_sweep_reversal_exploration_report(
        market_df,
        selection_report=selection_report,
        source=source,
    )
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    selected = report.get("selected_candidate") or {}
    metrics = selected.get("metrics", {}) if isinstance(selected, dict) else {}
    print(f"{HYP005_EXPLORATION_CONTRACT_VERSION} HYP-005 liquidity sweep reversal exploration {report['decision']}")
    print(f" - hypothesis_id: {report.get('hypothesis_id')}")
    print(f" - symbols: {','.join(report.get('symbols', []))}")
    print(f" - candidate_count: {report.get('candidate_count')}")
    print(f" - passed_candidate_count: {report.get('passed_candidate_count')}")
    print(f" - selected_strategy_family: {selected.get('strategy_family') if isinstance(selected, dict) else None}")
    print(f" - selected_signal_count: {metrics.get('signal_count')}")
    print(f" - selected_mean_net_edge_bps: {metrics.get('mean_net_edge_bps')}")
    print(f" - selected_median_net_edge_bps: {metrics.get('median_net_edge_bps')}")
    print(f" - selected_profit_factor: {metrics.get('profit_factor')}")
    print(f" - selected_oos_mean_net_edge_bps: {metrics.get('oos_mean_net_edge_bps')}")
    print(f" - selected_walk_forward_positive_rate_pct: {metrics.get('walk_forward_positive_rate_pct')}")
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
