from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tradebot.futures_branch_closure_evidence_pack import (
    build_futures_branch_closure_evidence_pack,
    discover_reports,
    load_json_report,
    write_report_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25H futures branch closure evidence pack")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25B/25C/25D/25E/25F/25G report JSON path. Can be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Directory to discover branch reports from.")
    parser.add_argument("--include-all", action="store_true", help="Include all matching reports under --reports-dir instead of only latest per phase.")
    parser.add_argument("--out-dir", default="reports", help="Output directory for the evidence pack.")
    parser.add_argument("--hypothesis-id", default="HYP-002")
    parser.add_argument("--branch-name", default="futures_funding_trend_exhaustion")
    parser.add_argument("--review-ok", action="store_true", help="Required explicit acknowledgement that this is no-order closure evidence only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This tool is observation-only closure evidence; it does not approve paper/live trading.", file=sys.stderr)
        return 2
    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(args.reports_dir, include_all=args.include_all))
    if not paths:
        print("ERROR: provide --input-json or --reports-dir", file=sys.stderr)
        return 2
    reports = [load_json_report(path) for path in paths]
    pack = build_futures_branch_closure_evidence_pack(
        reports,
        hypothesis_id=args.hypothesis_id,
        branch_name=args.branch_name,
    )
    report_json, report_md = write_report_bundle(pack, out_dir=args.out_dir)
    print(f"4B.4.3.6.6.25H futures branch closure evidence pack {pack['decision']}")
    print(f" - source_reports: {pack['source_reports']}")
    print(f" - hypothesis_id: {pack['hypothesis_id']}")
    print(f" - branch_name: {pack['branch_name']}")
    print(f" - final_25f_decision: {pack['final_25f_decision']}")
    print(f" - primary_terminal_block_count: {pack['primary_terminal_block_count']}")
    print(f" - companion_terminal_block_count: {pack['companion_terminal_block_count']}")
    print(f" - approved_for_research_candidate: {pack['approved_for_research_candidate']}")
    print(f" - approved_for_training_candidate: {pack['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {pack['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {pack['approved_for_live_real']}")
    print(f" - reason_codes: {pack['reason_codes']}")
    print(f" - recommendation: {pack['recommendation']}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
