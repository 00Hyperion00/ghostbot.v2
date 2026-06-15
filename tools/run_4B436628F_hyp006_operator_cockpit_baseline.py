from __future__ import annotations

import argparse
from pathlib import Path

from tradebot.hyp006_operator_cockpit_baseline import (
    build_acceptance_baseline_report,
    load_json,
    load_jsonl,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28F HYP-006-R1 operator cockpit dashboard seed / acceptance baseline")
    parser.add_argument("--scheduler-health-json", required=True)
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--operator-dashboard-review", action="store_true", help="Required explicit operator review acknowledgement")
    parser.add_argument("--review-ok", action="store_true", help="Required explicit review acknowledgement")
    args = parser.parse_args()

    if not args.operator_dashboard_review or not args.review_ok:
        raise SystemExit("28F requires --operator-dashboard-review and --review-ok")

    health_report = load_json(args.scheduler_health_json)
    ledger_rows = load_jsonl(args.ledger_jsonl)
    payload = build_acceptance_baseline_report(
        health_report=health_report,
        ledger_rows=ledger_rows,
        source_paths={
            "scheduler_health_json": str(Path(args.scheduler_health_json).resolve()),
            "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
        },
    )
    report_json, dashboard_json, acceptance_json, continuity_json, report_md = write_report_bundle(payload, args.out_dir)

    print(f"4B.4.3.6.6.28F HYP-006-R1 operator cockpit baseline {payload['decision']}")
    for key in (
        "read_only",
        "dashboard_seed_ready",
        "acceptance_baseline_ready",
        "no_order_continuity_monitor_ready",
        "approved_for_shadow_collection_continuity",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "next_required_gate",
    ):
        print(f" - {key}: {payload.get(key)}")
    summary = payload.get("baseline_summary", {})
    baseline = payload.get("acceptance_baseline_metrics", {})
    print(f" - ledger_row_count: {summary.get('ledger_row_count')}")
    print(f" - unique_observation_ids: {summary.get('unique_observation_ids')}")
    print(f" - mean_return_bps: {summary.get('mean_return_bps')}")
    print(f" - profit_factor: {summary.get('profit_factor')}")
    print(f" - acceptance_requirements_met: {baseline.get('acceptance_requirements_met')}")
    print(f" - blockers: {payload.get('blockers')}")
    print(f"report_json: {report_json}")
    print(f"dashboard_seed_json: {dashboard_json}")
    print(f"acceptance_baseline_json: {acceptance_json}")
    print(f"continuity_monitor_json: {continuity_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
