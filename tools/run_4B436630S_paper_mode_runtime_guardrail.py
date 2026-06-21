from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.paper_mode_runtime_guardrail import CONTRACT_VERSION, build_from_latest_30r_reconciliation_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30r_reconciliation_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Mode Runtime Guardrail {payload.get('decision')}")
    for key in (
        "approved_for_paper_mode_runtime_guardrail",
        "source_30r_reconciliation_verified",
        "guarded_runtime_loop_verified",
        "strict_caps_verified",
        "kill_switch_verified",
        "loop_tick_count",
        "order_action_count",
        "exchange_submit_count",
        "network_submit_count",
        "approved_for_exchange_submit",
        "approved_for_live_real",
        "exchange_submit_performed",
        "network_submit_attempted",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload.get("decision") == "PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
