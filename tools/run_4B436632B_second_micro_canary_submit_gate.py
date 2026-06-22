from __future__ import annotations

import argparse
import json
from typing import Any

from tradebot.second_micro_canary_submit_gate import (
    DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT,
    DEFAULT_MIN_QUANTITY,
    DEFAULT_ORDER_TYPE,
    DEFAULT_QUANTITY_STEP,
    DEFAULT_REPORTS_DIR,
    DEFAULT_SIDE,
    DEFAULT_SYMBOL,
    READY_DECISION,
    build_from_explicit_32a_report,
    build_from_latest_32a_report,
    write_report_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.32B second micro-canary submit gate runner")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--source-32a-report", default=None, help="Explicit accepted 32A READY JSON report path")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--finalization-token", default=None)
    parser.add_argument("--operator-approval-id", default=None)
    parser.add_argument("--operator-approve-submit-request", action="store_true", help="Approves evidence-only submit request generation, not exchange submit")
    parser.add_argument("--emergency-stop-armed", action="store_true")
    parser.add_argument("--audit-comment", default=None)
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--side", default=DEFAULT_SIDE)
    parser.add_argument("--order-type", default=DEFAULT_ORDER_TYPE)
    parser.add_argument("--reference-price", type=float, required=True)
    parser.add_argument("--requested-notional-usdt", type=float, default=None)
    parser.add_argument("--exchange-min-notional-usdt", default=str(DEFAULT_EXCHANGE_MIN_NOTIONAL_USDT))
    parser.add_argument("--quantity-step", default=str(DEFAULT_QUANTITY_STEP))
    parser.add_argument("--min-quantity", default=str(DEFAULT_MIN_QUANTITY))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    kwargs: dict[str, Any] = {
        "reports_dir": args.reports_dir,
        "operator_id": args.operator_id,
        "finalization_token": args.finalization_token,
        "emergency_stop_armed": args.emergency_stop_armed,
        "operator_approve_submit_request": args.operator_approve_submit_request,
        "operator_approval_id": args.operator_approval_id,
        "audit_comment": args.audit_comment,
        "symbol": args.symbol,
        "side": args.side,
        "order_type": args.order_type,
        "reference_price": args.reference_price,
        "requested_notional_usdt": args.requested_notional_usdt,
        "exchange_min_notional_usdt": args.exchange_min_notional_usdt,
        "quantity_step": args.quantity_step,
        "min_quantity": args.min_quantity,
    }
    if args.source_32a_report:
        payload = build_from_explicit_32a_report(source_32a_report=args.source_32a_report, **kwargs)
    else:
        payload = build_from_latest_32a_report(**kwargs)
    json_path, md_path = write_report_bundle(payload, reports_dir=args.reports_dir)
    payload["report_json_path"] = str(json_path)
    payload["report_markdown_path"] = str(md_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("decision") == READY_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main())
