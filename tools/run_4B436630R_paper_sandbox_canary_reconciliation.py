from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.paper_sandbox_canary_reconciliation import CONTRACT_VERSION, build_from_latest_30q_ready_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30q_ready_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Sandbox Canary Reconciliation {payload.get('decision')}")
    for key in (
        "approved_for_paper_sandbox_canary_reconciliation",
        "source_30q_canary_gate_verified",
        "canary_order_intent_consumed",
        "intent_fill_account_reconciled",
        "submit_remained_guarded_verified",
        "mismatch_count",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "exchange_submit_performed",
        "network_submit_attempted",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
