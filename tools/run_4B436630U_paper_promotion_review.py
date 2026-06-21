from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.paper_promotion_review import CONTRACT_VERSION, build_from_latest_30t_soak_report, write_report_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    payload = build_from_latest_30t_soak_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Paper Promotion Review {payload.get('decision')}")
    for key in (
        "approved_for_paper_promotion_review",
        "approved_for_paper_runtime_promotion_candidate",
        "source_30t_soak_verified",
        "risk_acceptance_gates_verified",
        "promotion_readiness_review_verified",
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
    print(f" - json_report: {json_path}")
    print(f" - markdown_report: {md_path}")
    return 0 if payload.get("approved_for_paper_promotion_review") and payload.get("approved_for_exchange_submit") is False and payload.get("approved_for_live_real") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
