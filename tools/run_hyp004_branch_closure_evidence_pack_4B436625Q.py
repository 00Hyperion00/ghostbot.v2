from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp004_branch_closure_evidence_pack import (  # noqa: E402
    build_hyp004_branch_closure_evidence_pack,
    discover_reports,
    load_json_report,
    write_report_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25Q HYP-004 branch closure evidence pack")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25O/25P JSON report path. Can be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Directory to scan for 25O/25P JSON reports.")
    parser.add_argument("--include-all", action="store_true", help="Use all matching 25O/25P reports instead of latest per phase.")
    parser.add_argument("--out-dir", default="reports", help="Output directory.")
    parser.add_argument("--hypothesis-id", default="HYP-004")
    parser.add_argument("--branch-name", default="cross_symbol_relative_strength_rotation")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is closure-only and no trading permissions are granted.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This closure pack is no-order and grants no paper/live permission.", file=sys.stderr)
        return 2

    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(args.reports_dir, include_all=args.include_all))
    # preserve order, de-dup
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)
    if not unique_paths:
        print("ERROR: provide --input-json or --reports-dir with 25O/25P reports", file=sys.stderr)
        return 2

    reports = [load_json_report(path) for path in unique_paths]
    report = build_hyp004_branch_closure_evidence_pack(
        reports,
        hypothesis_id=args.hypothesis_id,
        branch_name=args.branch_name,
    )
    report_json, report_md, registry_snapshot_json = write_report_bundle(report, out_dir=args.out_dir)

    print(f"4B.4.3.6.6.25Q HYP-004 branch closure evidence pack {report.decision}")
    print(f" - source_reports: {report.source_reports}")
    print(f" - hypothesis_id: {report.hypothesis_id}")
    print(f" - branch_name: {report.branch_name}")
    print(f" - final_25o_decision: {report.final_25o_decision}")
    print(f" - final_25p_decision: {report.final_25p_decision}")
    print(f" - selected_25o_family: {report.selected_25o_family}")
    print(f" - selected_refinement_name: {report.selected_refinement_name}")
    print(f" - no_approvable_exploration_candidate_confirmed: {report.no_approvable_exploration_candidate_confirmed}")
    print(f" - no_approvable_refinement_candidate_confirmed: {report.no_approvable_refinement_candidate_confirmed}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - reason_codes: {list(report.reason_codes)}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"registry_snapshot_json: {registry_snapshot_json}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
