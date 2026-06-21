from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.paper_soak_evidence_window import CONTRACT_VERSION, READY_DECISION, build_from_latest_30s_guardrail_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30s_guardrail_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Soak / Evidence Window {payload.get('decision')}")
    for key in (
        "approved_for_paper_soak_evidence_window",
        "source_30s_guardrail_verified",
        "multi_cycle_soak_verified",
        "cap_continuity_verified",
        "kill_switch_continuity_verified",
        "soak_cycle_count",
        "minimum_soak_cycles_required",
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
    return 0 if payload.get("decision") == READY_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
