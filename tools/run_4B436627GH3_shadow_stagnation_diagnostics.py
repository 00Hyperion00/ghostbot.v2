from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_shadow_stagnation_diagnostics import (  # noqa: E402
    CONTRACT_VERSION,
    REPORT_PREFIX,
    Candle,
    build_stagnation_diagnostics_report,
    fetch_public_klines,
    load_json,
    load_jsonl,
    parse_csv_rows,
    parse_runtime_spec,
    utc_now_iso,
    write_json_atomic,
    write_markdown,
)


def _parse_symbols(text: str | None) -> list[str]:
    if not text:
        return []
    return [item.strip().upper() for item in text.split(",") if item.strip()]


def _load_candles(args: argparse.Namespace, candidate_spec: dict[str, Any] | None) -> tuple[list[Candle], bool, list[str]]:
    warnings: list[str] = []
    if args.input_csv:
        symbols = _parse_symbols(args.symbols)
        default_symbol = symbols[0] if symbols else "TESTUSDT"
        return parse_csv_rows(args.input_csv, default_symbol=default_symbol), False, warnings
    if args.offline:
        warnings.append("PUBLIC_MARKET_DATA_FETCH_DISABLED_OFFLINE_MODE")
        return [], False, warnings
    spec = parse_runtime_spec(candidate_spec)
    symbols = _parse_symbols(args.symbols)
    if not symbols:
        symbols = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
    candles: list[Candle] = []
    network_used = False
    for symbol in symbols:
        try:
            rows = fetch_public_klines(
                symbol=symbol,
                interval=args.interval or spec.timeframe,
                days=args.days,
                base_url=args.base_url,
                timeout_sec=args.timeout_sec,
            )
            network_used = True
            candles.extend(rows)
        except Exception as exc:  # noqa: BLE001 - public GET failure is reported, not hidden.
            warnings.append(f"PUBLIC_MARKET_DATA_GET_FAILED_{symbol}:{exc}")
    return candles, network_used, warnings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.27G-H3 HYP-005-R1 stagnation / near-miss diagnostics")
    parser.add_argument("--candidate-spec-json", type=Path, required=True)
    parser.add_argument("--ledger-jsonl", type=Path, required=True)
    parser.add_argument("--input-csv", type=Path, default=None, help="Optional deterministic OHLCV CSV. Disables public fetch.")
    parser.add_argument("--symbols", default="ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT")
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--timeout-sec", type=int, default=15)
    parser.add_argument("--out-dir", type=Path, default=Path("reports/hyp005_r1_canonical"))
    parser.add_argument("--offline", action="store_true", help="Do not perform public market-data GET when no CSV is supplied.")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement: no-order diagnostics only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 27G-H3 is no-order research diagnostics only.", file=sys.stderr)
        return 2
    if not args.candidate_spec_json.exists():
        print(f"ERROR: candidate spec not found: {args.candidate_spec_json}", file=sys.stderr)
        return 2
    if not args.ledger_jsonl.exists():
        print(f"ERROR: ledger jsonl not found: {args.ledger_jsonl}", file=sys.stderr)
        return 2

    candidate_spec = load_json(args.candidate_spec_json)
    ledger_rows = load_jsonl(args.ledger_jsonl)
    candles, network_used, warnings = _load_candles(args, candidate_spec if isinstance(candidate_spec, dict) else None)
    generated_at = utc_now_iso()
    report = build_stagnation_diagnostics_report(
        candidate_spec=candidate_spec if isinstance(candidate_spec, dict) else None,
        ledger_rows=ledger_rows,
        candles=candles,
        generated_at=generated_at,
    )
    report["network_request_performed"] = network_used
    report["source_paths"] = {
        "candidate_spec_json": str(args.candidate_spec_json.resolve()),
        "ledger_jsonl": str(args.ledger_jsonl.resolve()),
        "input_csv": None if args.input_csv is None else str(args.input_csv.resolve()),
    }
    report["warnings"] = sorted(set([*report.get("warnings", []), *warnings]))
    if not candles:
        report["reason_codes"] = sorted(set([*report.get("reason_codes", []), "DIAGNOSTIC_CANDLES_MISSING"]))
        report["recommendation"] = "No candles were available for stagnation diagnostics. Provide --input-csv or allow public GET; keep paper/live gates closed."

    stamp = generated_at.replace("+00:00", "Z").replace(":", "").replace("-", "")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_json = args.out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = args.out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, report)
    write_markdown(report_md, report)

    print(f"{CONTRACT_VERSION} HYP-005-R1 shadow stagnation diagnostics {report['decision']}")
    print(f" - read_only: {report['read_only']}")
    print(f" - no_order_research_diagnostics_only: {report['no_order_research_diagnostics_only']}")
    print(f" - network_request_performed: {report['network_request_performed']}")
    print(f" - shadow_observation_count: {report['ledger_summary']['shadow_observation_count']}")
    print(f" - latest_observation_utc: {report['ledger_summary']['latest_observation_utc']}")
    print(f" - stagnation_status: {report['stagnation']['status']}")
    print(f" - evaluated_candle_count: {report['candidate_diagnostics']['evaluated_candle_count']}")
    print(f" - exact_candidate_count: {report['candidate_diagnostics']['exact_candidate_count']}")
    print(f" - new_unique_candidate_count: {report['candidate_diagnostics']['new_unique_candidate_count']}")
    print(f" - duplicate_candidate_count: {report['candidate_diagnostics']['duplicate_candidate_count']}")
    print(f" - near_miss_count: {report['candidate_diagnostics']['near_miss_count']}")
    print(f" - top_bottleneck_filter: {report['candidate_diagnostics']['top_bottleneck_filter']}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    print(" - approved_for_paper_candidate: False")
    print(" - approved_for_live_real: False")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if report.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(main())
