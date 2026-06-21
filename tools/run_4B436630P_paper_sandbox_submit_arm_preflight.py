from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.paper_sandbox_submit_arm_preflight import CONTRACT_VERSION, build_from_latest_30o_ready_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30o_ready_report(Settings(), reports_dir=args.reports_dir)
    report_json, report_md = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Sandbox Submit-Arm Preflight {payload.get('decision')}")
    for key in (
        "read_only",
        "approved_for_paper_sandbox_submit_arm_preflight",
        "approved_for_30o_reconciliation_proof_consumption",
        "approved_for_api_mode_check",
        "approved_for_endpoint_check",
        "approved_for_min_notional_check",
        "approved_for_lot_size_check",
        "approved_for_risk_caps_check",
        "approved_for_kill_switch_check",
        "approved_for_order_request_skeleton_build",
        "approved_for_exchange_submit",
        "approved_for_paper_sandbox_canary_submit",
        "approved_for_live_real",
        "submit_order_still_blocked",
        "exchange_submit_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
