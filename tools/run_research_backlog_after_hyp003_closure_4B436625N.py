from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_backlog_after_hyp003_closure import (  # noqa: E402
    build_research_backlog_after_hyp003_closure,
    discover_latest_hyp003_closure_report,
    load_json,
    write_report_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25N research backlog advancement after HYP-003 closure")
    parser.add_argument("--input-json", default=None, help="Explicit 25M HYP-003 closure evidence pack JSON.")
    parser.add_argument("--reports-dir", default="reports", help="Reports directory for latest 25M closure pack discovery.")
    parser.add_argument("--registry-json", default=None, help="Optional current research registry/backlog JSON.")
    parser.add_argument("--out-dir", default="reports", help="Output directory for report and registry snapshot.")
    parser.add_argument("--hypothesis-id", default="HYP-003", help="Closed hypothesis id, default HYP-003.")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is research-only and cannot approve training/paper/live.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This gate is research-only and cannot approve training/paper/live.", file=sys.stderr)
        return 2

    closure_path = Path(args.input_json) if args.input_json else discover_latest_hyp003_closure_report(args.reports_dir)
    if closure_path is None:
        print("ERROR: no HYP-003 closure evidence pack found. Provide --input-json or a reports directory containing 25M output.", file=sys.stderr)
        return 2

    closure_report = load_json(closure_path)
    registry = load_json(args.registry_json) if args.registry_json else None
    report = build_research_backlog_after_hyp003_closure(
        closure_report,
        registry=registry,
        hypothesis_id=args.hypothesis_id,
    )
    report_json, report_md, snapshot_json = write_report_bundle(report, out_dir=args.out_dir)

    print(f"4B.4.3.6.6.25N research backlog advancement {report['decision']}")
    print(f" - closure_report: {closure_path}")
    print(f" - closed_hypothesis_id: {report.get('closed_hypothesis_id')}")
    print(f" - closed_branch_name: {report.get('closed_branch_name')}")
    print(f" - selected_next_hypothesis_id: {report.get('selected_next_hypothesis_id')}")
    print(f" - selected_next_hypothesis_title: {report.get('selected_next_hypothesis_title')}")
    print(f" - selected_next_branch_name: {report.get('selected_next_branch_name')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"registry_snapshot_json: {snapshot_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
