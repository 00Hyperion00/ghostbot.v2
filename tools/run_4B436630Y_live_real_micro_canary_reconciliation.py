from __future__ import annotations

import argparse

from tradebot.config import Settings
from tradebot.live_real_micro_canary_reconciliation import (
    CONTRACT_VERSION,
    build_from_latest_30x_report_and_request,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--execution-evidence-json", default=None)
    parser.add_argument("--operator-executed", action="store_true")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--exchange-order-id", default=None)
    parser.add_argument("--client-order-id", default=None)
    parser.add_argument("--filled-quantity", default=None)
    parser.add_argument("--avg-fill-price", default=None)
    parser.add_argument("--account-position-delta-qty", default=None)
    parser.add_argument("--ledger-event-id", default=None)
    parser.add_argument("--ledger-filled-quantity", default=None)
    parser.add_argument("--ledger-notional-usd", default=None)
    parser.add_argument("--emergency-stop-armed", action="store_true")
    parser.add_argument("--emergency-stop-not-armed", action="store_true")
    parser.add_argument("--allow-min-notional-quantity-adjustment", action="store_true")
    parser.add_argument("--quantity-adjustment-reason", default=None)
    args = parser.parse_args()
    emergency_stop_armed = True if args.emergency_stop_armed else not bool(args.emergency_stop_not_armed)
    payload = build_from_latest_30x_report_and_request(
        Settings(),
        args.reports_dir,
        execution_evidence_json=args.execution_evidence_json,
        operator_executed=args.operator_executed,
        operator_id=args.operator_id,
        exchange_order_id=args.exchange_order_id,
        client_order_id=args.client_order_id,
        filled_quantity=args.filled_quantity,
        avg_fill_price=args.avg_fill_price,
        account_position_delta_qty=args.account_position_delta_qty,
        ledger_event_id=args.ledger_event_id,
        ledger_filled_quantity=args.ledger_filled_quantity,
        ledger_notional_usd=args.ledger_notional_usd,
        emergency_stop_armed=emergency_stop_armed,
        allow_min_notional_quantity_adjustment=args.allow_min_notional_quantity_adjustment,
        quantity_adjustment_reason=args.quantity_adjustment_reason,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(f"{CONTRACT_VERSION} Live-Real Micro Canary Reconciliation {payload.get('decision')}")
    for key in (
        "approved_for_live_real_micro_canary_reconciliation",
        "approved_for_post_canary_review",
        "approved_for_additional_exchange_submit",
        "approved_for_live_real_continuation",
        "source_30x_submit_request_verified",
        "execution_evidence_verified",
        "fill_reconciliation_verified",
        "account_reconciliation_verified",
        "ledger_reconciliation_verified",
        "mismatch_zero_verified",
        "emergency_stop_armed_verified",
        "mismatch_count",
        "external_exchange_submit_performed",
        "external_network_submit_attempted",
        "external_live_real_order_performed",
        "patch_exchange_submit_performed",
        "patch_network_submit_attempted",
        "patch_live_real_order_performed",
        "further_live_real_submit_blocked",
    ):
        print(f" - {key}: {payload.get(key)}")
    print(f" - json_report: {json_path}")
    print(f" - markdown_report: {md_path}")
    return 0 if payload.get("source_30x_submit_request_verified") and payload.get("patch_network_submit_attempted") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
