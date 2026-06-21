from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.live_real_preflight_gate import CONTRACT_VERSION, build_from_latest_30u_promotion_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30u_promotion_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Live-Real Preflight Gate {payload.get('decision')}")
    for key in (
        "approved_for_live_real_preflight_gate",
        "approved_for_live_real_readiness_candidate",
        "source_30u_promotion_review_verified",
        "api_env_capability_audit_verified",
        "account_capability_audit_verified",
        "hard_live_submit_block_verified",
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
    print(f" - json_report: {json_path}")
    print(f" - markdown_report: {md_path}")
    return 0 if payload.get("approved_for_live_real_preflight_gate") and payload.get("approved_for_exchange_submit") is False and payload.get("approved_for_live_real") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
