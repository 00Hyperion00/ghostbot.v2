from __future__ import annotations

import argparse
from pathlib import Path

from tradebot.config import Settings
from tradebot.first_paper_sandbox_canary_submit_gate import (
    CONTRACT_VERSION,
    build_from_latest_30p_ready_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--approval-token", default=None)
    parser.add_argument("--issue-canary-approval", action="store_true")
    parser.add_argument("--write-intent", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    args = parser.parse_args()
    settings = Settings()
    intent_path = Path(args.reports_dir) / "4B436630Q_single_canary_order_intent.json"
    payload = build_from_latest_30p_ready_report(
        settings,
        reports_dir=args.reports_dir,
        operator_id=args.operator_id,
        approval_token=args.approval_token,
        issue_canary_approval=args.issue_canary_approval,
        write_intent=args.write_intent,
        intent_path=intent_path,
        ttl_sec=args.ttl_sec,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} First Paper Sandbox Canary Submit Gate {payload.get('decision')}")
    for key in (
        "read_only",
        "approved_for_first_paper_sandbox_canary_submit_gate",
        "approved_for_30p_submit_arm_consumption",
        "approved_for_operator_canary_approval",
        "approved_for_single_sandbox_order_intent",
        "approved_for_sandbox_submit_path_armed_candidate",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "source_30p_submit_arm_verified",
        "sandbox_submit_readiness_verified",
        "single_sandbox_order_intent_built",
        "canary_order_intent_written",
        "exchange_submit_path_guarded",
        "submit_still_blocked",
        "exchange_submit_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    intent = payload.get("single_sandbox_order_intent", {})
    if isinstance(intent, dict):
        print(f"order_intent: {intent.get('intent_path')}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
