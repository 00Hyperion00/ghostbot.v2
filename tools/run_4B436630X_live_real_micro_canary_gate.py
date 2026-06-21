from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.live_real_micro_canary_gate import (
    APPROVAL_TOKEN,
    CONTRACT_VERSION,
    build_from_latest_30w_final_operator_approval_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--approval-token", default=None)
    parser.add_argument("--issue-micro-canary-approval", action="store_true")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--side", default=None)
    parser.add_argument("--quantity", default=None)
    parser.add_argument("--mark-price", default=None)
    parser.add_argument("--write-submit-request", action="store_true")
    args = parser.parse_args()
    payload = build_from_latest_30w_final_operator_approval_report(
        Settings(),
        args.reports_dir,
        operator_id=args.operator_id,
        approval_token=args.approval_token,
        issue_micro_canary_approval=args.issue_micro_canary_approval,
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        mark_price=args.mark_price,
        write_submit_request=args.write_submit_request,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} First Live-Real Micro Canary {payload.get('decision')}")
    for key in (
        "approved_for_first_live_real_micro_canary_gate",
        "approved_for_first_live_real_micro_canary_submit_request",
        "approved_for_manual_runtime_handoff",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "source_30w_final_operator_approval_verified",
        "micro_canary_operator_approval_verified",
        "single_min_size_order_request_verified",
        "hard_caps_verified",
        "kill_switch_verified",
        "automated_network_submit_disabled_verified",
        "submit_request_built",
        "submit_request_path",
        "submit_request_count",
        "total_notional_usd",
        "max_total_notional_usd",
        "order_action_count",
        "exchange_submit_count",
        "network_submit_count",
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
    return 0 if payload.get("source_30w_final_operator_approval_verified") and payload.get("exchange_submit_performed") is False and payload.get("network_submit_attempted") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
