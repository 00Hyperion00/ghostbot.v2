from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp006_scheduler_health_verify import (  # noqa: E402
    CONTRACT_VERSION,
    PROPOSED_SCHEDULER_TASK_NAME,
    build_scheduler_execution_health_report,
    load_json,
    load_jsonl,
    probe_windows_task_scheduler,
    write_health_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28E HYP-006-R1 scheduler execution health verify")
    parser.add_argument("--registration-approval-json", required=True)
    parser.add_argument("--cycle-report-json", required=True)
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--task-probe-json")
    parser.add_argument("--task-name", default=PROPOSED_SCHEDULER_TASK_NAME)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--operator-execution-review", action="store_true")
    parser.add_argument("--review-ok", action="store_true")
    args = parser.parse_args()
    if not args.review_ok:
        raise SystemExit("FAIL_CLOSED_REQUIRES_REVIEW_OK")
    if not args.operator_execution_review:
        raise SystemExit("FAIL_CLOSED_REQUIRES_OPERATOR_EXECUTION_REVIEW")
    registration_approval = load_json(args.registration_approval_json)
    cycle_report = load_json(args.cycle_report_json)
    ledger_rows = load_jsonl(args.ledger_jsonl)
    task_probe = load_json(args.task_probe_json) if args.task_probe_json else probe_windows_task_scheduler(args.task_name)
    payload = build_scheduler_execution_health_report(
        registration_approval_report=registration_approval,
        cycle_report=cycle_report,
        ledger_rows=ledger_rows,
        task_probe=task_probe,
        operator_execution_review=args.operator_execution_review,
        source_paths={
            "registration_approval_json": str(Path(args.registration_approval_json).resolve()),
            "cycle_report_json": str(Path(args.cycle_report_json).resolve()),
            "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
            "task_probe_json": None if not args.task_probe_json else str(Path(args.task_probe_json).resolve()),
        },
    )
    report_json, continuity_json, report_md = write_health_bundle(payload, args.out_dir)
    print(f"{CONTRACT_VERSION} HYP-006-R1 scheduler execution health {payload['decision']}")
    scheduler = payload.get("scheduler_task_health", {})
    ledger = payload.get("ledger_continuity_summary", {})
    for key in (
        "read_only",
        "no_order_scheduler_health_verify_only",
        "approved_for_shadow_collection_continuity",
        "scheduler_mutation_performed",
        "scheduler_task_created",
        "approved_for_paper_candidate",
        "approved_for_live_real",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f" - task_name: {scheduler.get('task_name')}")
    print(f" - last_task_result: {scheduler.get('last_task_result')}")
    print(f" - ledger_row_count: {ledger.get('ledger_row_count')}")
    print(f" - unique_observation_ids: {ledger.get('unique_observation_ids')}")
    print(f" - mean_return_bps: {ledger.get('mean_return_bps')}")
    print(f" - profit_factor: {ledger.get('profit_factor')}")
    print(f"report_json: {report_json}")
    print(f"ledger_continuity_json: {continuity_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
