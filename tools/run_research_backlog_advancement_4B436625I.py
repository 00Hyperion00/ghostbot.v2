from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_backlog_advancement import (
    DEFAULT_BRANCH_NAME,
    DEFAULT_CLOSED_HYPOTHESIS_ID,
    RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION,
    build_research_backlog_advancement_gate,
    discover_reports,
    load_backlog_from_registry,
    load_json,
    write_report_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25I research backlog advancement / next hypothesis selection gate")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit closure/evidence report JSON. Can be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Directory to discover recent 25H/25F/25G/25D/25E evidence reports.")
    parser.add_argument("--include-all", action="store_true", help="Use all matching reports under --reports-dir.")
    parser.add_argument("--registry-json", default=None, help="Optional research hypothesis registry JSON. Missing file falls back to built-in backlog.")
    parser.add_argument("--out-dir", default="reports", help="Output directory for report and proposed registry snapshot.")
    parser.add_argument("--hypothesis-id", default=DEFAULT_CLOSED_HYPOTHESIS_ID, help="Closed hypothesis id, default HYP-002.")
    parser.add_argument("--branch-name", default=DEFAULT_BRANCH_NAME, help="Closed branch name.")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is research-only and grants no trading permission.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This gate is research-only and does not approve training/paper/live trading.", file=sys.stderr)
        return 2

    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(args.reports_dir, include_all=args.include_all))
    if not paths:
        print("ERROR: provide --input-json or --reports-dir", file=sys.stderr)
        return 2

    reports = [(str(path), load_json(path)) for path in paths]
    backlog, registry_source = load_backlog_from_registry(args.registry_json)
    report = build_research_backlog_advancement_gate(
        reports,
        backlog=backlog,
        registry_source=registry_source,
        hypothesis_id=args.hypothesis_id,
        branch_name=args.branch_name,
    )
    report_json, report_md, registry_json = write_report_bundle(report, args.out_dir)

    print(f"{RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION} research backlog advancement {report.decision}")
    print(f" - source_reports: {report.source_reports}")
    print(f" - registry_source: {report.registry_source}")
    print(f" - closed_hypothesis_id: {report.closed_hypothesis_id}")
    print(f" - closed_branch_name: {report.closed_branch_name}")
    print(f" - selected_next_hypothesis_id: {report.selected_next_hypothesis_id}")
    print(f" - selected_next_hypothesis_title: {report.selected_next_hypothesis_title}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - reason_codes: {list(report.reason_codes)}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"proposed_registry_json: {registry_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
