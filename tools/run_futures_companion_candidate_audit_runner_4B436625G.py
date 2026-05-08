from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tradebot.futures_companion_candidate_audit_runner import (
    DEFAULT_COMPANION_SYMBOLS,
    DEFAULT_INTERVAL,
    DEFAULT_PRIMARY_SYMBOL,
    DEFAULT_STRATEGY,
    build_futures_companion_candidate_audit_runner,
    discover_reports,
    load_json_report,
    write_json,
    write_report_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25G futures companion candidate audit runner")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25B/25C/25D/25E report JSON path. Can be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Directory to discover recent 25B/25C/25D/25E reports from.")
    parser.add_argument("--include-all", action="store_true", help="Include all matching reports under --reports-dir instead of only latest per phase.")
    parser.add_argument("--out-dir", default="reports", help="Output directory for report/spec files.")
    parser.add_argument("--primary-symbol", default=DEFAULT_PRIMARY_SYMBOL)
    parser.add_argument("--companion-symbols", default=",".join(DEFAULT_COMPANION_SYMBOLS))
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://fapi.binance.com")
    parser.add_argument("--review-ok", action="store_true", help="Required explicit acknowledgement that output is no-order research only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This tool is observation-only and does not approve paper/live trading.", file=sys.stderr)
        return 2

    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(args.reports_dir, include_all=args.include_all))
    if not paths:
        print("ERROR: provide --input-json or --reports-dir", file=sys.stderr)
        return 2

    reports = [load_json_report(path) for path in paths]
    companion_symbols = [item.strip() for item in str(args.companion_symbols).split(",") if item.strip()]
    out_dir = Path(args.out_dir)
    spec_path = out_dir / f"4B436625G_companion_spec_{companion_symbols[0] if companion_symbols else 'UNKNOWN'}_{args.interval}_{args.strategy}.json"

    report = build_futures_companion_candidate_audit_runner(
        reports,
        primary_symbol=args.primary_symbol,
        companion_symbols=companion_symbols,
        interval=args.interval,
        strategy=args.strategy,
        days=args.days,
        base_url=args.base_url,
        out_dir=args.out_dir,
        spec_path=str(spec_path),
    )

    if report.get("companion_spec"):
        write_json(spec_path, report["companion_spec"])
        print(f"spec_json: {spec_path}")

    report_json, report_md = write_report_bundle(report, out_dir=out_dir)
    print(f"4B.4.3.6.6.25G futures companion audit runner {report['decision']}")
    print(f" - source_reports: {report['source_reports']}")
    print(f" - primary: {(report.get('primary') or {}).get('symbol')} {(report.get('primary') or {}).get('interval')} {(report.get('primary') or {}).get('strategy')}")
    print(f" - companion: {(report.get('companion') or {}).get('symbol')} {(report.get('companion') or {}).get('interval')} {(report.get('companion') or {}).get('strategy')}")
    print(f" - combined_signals: {report.get('combined_signals')}")
    print(f" - downstream_confirmed_count: {report.get('downstream_confirmed_count')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
