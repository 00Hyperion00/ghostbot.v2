from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

HYP003_REFINEMENT_CLI_HOTFIX_VERSION = "4B.4.3.6.6.25L-H1"

from tradebot.research_hyp003_candidate_refinement_branch_decision import (  # noqa: E402
    NEXT_CANDIDATE_PREFIX,
    REPORT_PREFIX,
    build_hyp003_candidate_refinement_branch_decision,
    discover_reports,
    load_json_report,
    render_markdown,
    write_json,
)


def _candidate_key_text(candidate: object) -> str:
    """Return a safe printable candidate key.

    25L-H1 fixes the closure path where selected_next_candidate is None.
    The base 25L CLI used selected_key.get(...) even when selected_key was None,
    causing AttributeError after a valid HYP003_BRANCH_CLOSURE_RECOMMENDED report.
    """
    if not isinstance(candidate, dict):
        return "NONE"
    key = candidate.get("key")
    if not isinstance(key, dict):
        return "NONE"
    return " ".join(
        str(key.get(part) or "NONE")
        for part in ("symbol", "interval", "strategy_family", "regime")
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25L HYP-003 candidate refinement / branch decision gate")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25J/25K report JSON. May be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Reports directory to discover latest 25J/25K reports.")
    parser.add_argument("--include-all", action="store_true", help="Include all matching 25J/25K reports instead of latest per phase.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is research-only and no trading/model action is performed.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 25L is research-only and does not approve training/paper/live trading.", file=sys.stderr)
        return 2
    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(args.reports_dir, include_all=args.include_all))
    if not paths:
        print("ERROR: provide --input-json or --reports-dir", file=sys.stderr)
        return 2
    reports = [load_json_report(path) for path in paths]
    report = build_hyp003_candidate_refinement_branch_decision(reports)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json(report_json, report)
    report_md.write_text(render_markdown(report), encoding="utf-8")
    next_report_path = None
    if report.get("next_candidate_25k_report"):
        next_report_path = out_dir / f"{NEXT_CANDIDATE_PREFIX}_{stamp}.json"
        write_json(next_report_path, report["next_candidate_25k_report"])
    print(f"4B.4.3.6.6.25L HYP-003 candidate refinement / branch decision {report['decision']}")
    print(f" - source_reports: {report['source_reports']}")
    print(f" - failed_candidate: {_candidate_key_text(report.get('failed_candidate'))}")
    print(f" - selected_next_candidate: {_candidate_key_text(report.get('selected_next_candidate'))}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    if next_report_path:
        print(f"next_candidate_25k_json: {next_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
