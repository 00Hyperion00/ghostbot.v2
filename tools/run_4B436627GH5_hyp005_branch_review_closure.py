from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_branch_review_closure import (  # noqa: E402
    CONTRACT_VERSION,
    REPORT_PREFIX,
    build_branch_review_closure_report,
    load_json,
    load_jsonl,
    write_json_atomic,
    write_markdown,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.27G-H5 HYP-005-R1 branch review closure decision pack")
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--h3-diagnostics-json", required=True)
    parser.add_argument("--h4-sensitivity-json", required=True)
    parser.add_argument("--operator-snapshot-json", default=None)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 27G-H5 is branch review evidence only and cannot close/promote/mutate anything.", file=sys.stderr)
        return 2
    ledger_rows = load_jsonl(args.ledger_jsonl)
    h3 = load_json(args.h3_diagnostics_json)
    h4 = load_json(args.h4_sensitivity_json)
    snapshot = load_json(args.operator_snapshot_json) if args.operator_snapshot_json else None
    report = build_branch_review_closure_report(
        ledger_rows=ledger_rows,
        h3_report=h3,
        h4_report=h4,
        operator_snapshot=snapshot,
    )
    report["source_paths"] = {
        "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
        "h3_diagnostics_json": str(Path(args.h3_diagnostics_json).resolve()),
        "h4_sensitivity_json": str(Path(args.h4_sensitivity_json).resolve()),
        "operator_snapshot_json": None if args.operator_snapshot_json is None else str(Path(args.operator_snapshot_json).resolve()),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["generated_at_utc"].replace("-", "").replace(":", "").replace("+0000", "Z").replace("+00:00", "Z")
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, report)
    write_markdown(report_md, report)
    print(f"{CONTRACT_VERSION} HYP-005-R1 branch review closure {report['decision']}")
    print(f" - read_only: {report['read_only']}")
    print(f" - no_order_branch_review_only: {report['no_order_branch_review_only']}")
    print(f" - branch_closure_recommended: {report['branch_closure_recommended']}")
    print(f" - closure_status: {report['closure_status']}")
    print(f" - operator_review_required_for_closure: {report['operator_review_required_for_closure']}")
    print(f" - strategy_parameter_mutation_performed: {report['strategy_parameter_mutation_performed']}")
    print(f" - branch_state_mutation_performed: {report['branch_state_mutation_performed']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if report.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(main())

# marker inventory: no-order branch-review-only --review-ok no paper/live/order/config/scheduler mutation
