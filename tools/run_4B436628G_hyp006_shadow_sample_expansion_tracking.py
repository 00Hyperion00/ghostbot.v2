from __future__ import annotations

import argparse
from pathlib import Path

from tradebot.hyp006_shadow_sample_expansion_tracking import (
    build_shadow_sample_expansion_report,
    load_json,
    load_jsonl,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28G HYP-006-R1 shadow sample expansion / acceptance tracking")
    parser.add_argument("--operator-cockpit-baseline-json", required=True)
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--operator-continuity-review", action="store_true", help="Required explicit operator continuity review acknowledgement")
    parser.add_argument("--review-ok", action="store_true", help="Required explicit review acknowledgement")
    args = parser.parse_args()

    if not args.operator_continuity_review or not args.review_ok:
        raise SystemExit("28G requires --operator-continuity-review and --review-ok")

    baseline_report = load_json(args.operator_cockpit_baseline_json)
    ledger_rows = load_jsonl(args.ledger_jsonl)
    payload = build_shadow_sample_expansion_report(
        baseline_report=baseline_report,
        ledger_rows=ledger_rows,
        source_paths={
            "operator_cockpit_baseline_json": str(Path(args.operator_cockpit_baseline_json).resolve()),
            "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
        },
    )
    report_json, acceptance_json, continuity_json, dashboard_json, report_md = write_report_bundle(payload, args.out_dir)

    print(f"4B.4.3.6.6.28G HYP-006-R1 shadow sample expansion tracking {payload['decision']}")
    for key in (
        "read_only",
        "sample_expansion_tracking_ready",
        "acceptance_tracking_ready",
        "operator_cockpit_continuity_delta_ready",
        "approved_for_shadow_collection_continuity",
        "approved_for_acceptance_tracking",
        "approved_for_acceptance_review_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "next_required_gate",
    ):
        print(f" - {key}: {payload.get(key)}")
    summary = payload.get("baseline_summary", {})
    delta = payload.get("sample_expansion_delta", {})
    acceptance = payload.get("acceptance_tracking_metrics", {})
    print(f" - previous_unique_observation_ids: {delta.get('previous_unique_observation_ids')}")
    print(f" - current_unique_observation_ids: {delta.get('current_unique_observation_ids')}")
    print(f" - new_unique_observation_count: {delta.get('new_unique_observation_count')}")
    print(f" - target_remaining_count: {delta.get('target_remaining_count')}")
    print(f" - mean_return_bps: {summary.get('mean_return_bps')}")
    print(f" - profit_factor: {summary.get('profit_factor')}")
    print(f" - acceptance_requirements_met: {acceptance.get('acceptance_requirements_met')}")
    print(f" - blockers: {payload.get('blockers')}")
    print(f"report_json: {report_json}")
    print(f"acceptance_tracking_delta_json: {acceptance_json}")
    print(f"continuity_delta_json: {continuity_json}")
    print(f"dashboard_delta_seed_json: {dashboard_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
