from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.live_real_final_operator_approval import (
    APPROVAL_TOKEN,
    CONTRACT_VERSION,
    build_from_latest_30v_preflight_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--approval-token", default=None)
    parser.add_argument("--issue-final-approval", action="store_true")
    args = parser.parse_args()
    payload = build_from_latest_30v_preflight_report(
        Settings(),
        args.reports_dir,
        operator_id=args.operator_id,
        approval_token=args.approval_token,
        issue_final_approval=args.issue_final_approval,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Live-Real Final Operator Approval {payload.get('decision')}")
    for key in (
        "approved_for_live_real_final_operator_approval",
        "approved_for_30x_live_real_micro_canary_candidate",
        "source_30v_live_real_preflight_verified",
        "final_operator_approval_verified",
        "hard_live_submit_block_verified",
        "live_real_submit_blocked_until_30x",
        "order_action_count",
        "exchange_submit_count",
        "network_submit_count",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "exchange_submit_performed",
        "network_submit_attempted",
        "live_real_order_performed",
        "live_real_order_submitted",
        "live_real_network_submit_attempted",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f" - expected_approval_token: {APPROVAL_TOKEN}")
    print(f" - json_report: {json_path}")
    print(f" - markdown_report: {md_path}")
    return 0 if payload.get("source_30v_live_real_preflight_verified") and payload.get("approved_for_exchange_submit") is False and payload.get("approved_for_live_real") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
