from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_shadow_parameter_sensitivity import (  # noqa: E402
    CONTRACT_VERSION,
    REPORT_PREFIX,
    _parse_float_csv,
    build_parameter_sensitivity_report,
    fetch_public_klines,
    load_json,
    load_jsonl,
    parse_csv_rows,
    write_json_atomic,
    write_markdown,
)


def _parse_symbols(text: str) -> list[str]:
    return [item.strip().upper() for item in text.split(",") if item.strip()]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.27G-H4 no-order parameter sensitivity matrix")
    parser.add_argument("--candidate-spec-json", required=True)
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--symbols", default="ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=int, default=15)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--min-sweep-bps-values", default="18,15,12")
    parser.add_argument("--min-wick-pct-values", default="42,38,35")
    parser.add_argument("--max-compression-ratio-values", default="1.05,1.10,1.15")
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args(argv)


def _load_candles(args: argparse.Namespace, symbols: list[str]) -> tuple[list[Any], bool]:
    if args.input_csv:
        default_symbol = symbols[0] if symbols else "TESTUSDT"
        return parse_csv_rows(args.input_csv, default_symbol=default_symbol), False
    candles: list[Any] = []
    for symbol in symbols:
        try:
            candles.extend(
                fetch_public_klines(
                    symbol=symbol,
                    interval=args.interval,
                    days=args.days,
                    base_url=args.base_url,
                    timeout_sec=args.timeout_sec,
                )
            )
        except Exception as exc:  # noqa: BLE001 - optional public market-data GET failure has no side effects.
            print(f"warning: optional public market-data GET failed for {symbol}: {exc}", file=sys.stderr)
    return candles, True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 27G-H4 is no-order research-only and cannot approve paper/live trading.", file=sys.stderr)
        return 2
    symbols = _parse_symbols(args.symbols)
    candidate_spec = load_json(args.candidate_spec_json)
    ledger_rows = load_jsonl(args.ledger_jsonl)
    candles, network = _load_candles(args, symbols)
    report = build_parameter_sensitivity_report(
        candidate_spec=candidate_spec,
        ledger_rows=ledger_rows,
        candles=candles,
        min_sweep_bps_values=_parse_float_csv(args.min_sweep_bps_values, (18.0, 15.0, 12.0)),
        min_wick_pct_values=_parse_float_csv(args.min_wick_pct_values, (42.0, 38.0, 35.0)),
        max_compression_ratio_values=_parse_float_csv(args.max_compression_ratio_values, (1.05, 1.10, 1.15)),
    )
    report["network_request_performed"] = network
    report["source_paths"] = {
        "candidate_spec_json": str(Path(args.candidate_spec_json).resolve()),
        "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
        "input_csv": None if args.input_csv is None else str(Path(args.input_csv).resolve()),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at_utc"].replace("-", "").replace(":", "").replace("+0000", "Z").replace("+00:00", "Z")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, report)
    write_markdown(report_md, report)
    summary = report["research_summary"]
    print(f"{CONTRACT_VERSION} HYP-005-R1 no-order parameter sensitivity matrix {report['decision']}")
    print(f" - read_only: {report['read_only']}")
    print(f" - no_order_research_variant_report_only: {report['no_order_research_variant_report_only']}")
    print(f" - network_request_performed: {report['network_request_performed']}")
    print(f" - variant_count: {summary['variant_count']}")
    print(f" - baseline_variant_id: {summary['baseline_variant_id']}")
    print(f" - variants_with_new_unique_candidates: {summary['variants_with_new_unique_candidates']}")
    print(f" - promising_research_only_variant_count: {summary['promising_research_only_variant_count']}")
    print(f" - best_research_variant_id: {summary['best_research_variant_id']}")
    print(f" - best_research_status: {summary['best_research_status']}")
    print(f" - paper_transition_candidate_found: {summary['paper_transition_candidate_found']}")
    print(f" - strategy_parameter_mutation_performed: {report['strategy_parameter_mutation_performed']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if report.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(main())

# marker inventory: method="GET" public_market_data_GET_only no-order research-only --review-ok
