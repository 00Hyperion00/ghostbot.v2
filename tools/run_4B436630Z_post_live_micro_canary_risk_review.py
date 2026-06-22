from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.post_live_micro_canary_risk_review import (  # noqa: E402
    DEFAULT_REPORTS_DIR,
    build_from_latest_30y_h1_reconciliation,
    build_post_live_micro_canary_risk_review_snapshot,
    load_json,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B.4.3.6.6.30Z post live micro-canary risk review evidence.")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--source-30y-report", default=None)
    parser.add_argument("--fee-amount", type=float, default=None)
    parser.add_argument("--fee-asset", default=None)
    parser.add_argument("--review-mark-price", type=float, default=None)
    parser.add_argument("--reference-price", type=float, default=None)
    parser.add_argument("--emergency-stop-armed", action="store_true")
    parser.add_argument("--kill-switch-not-armed", action="store_true")
    parser.add_argument("--additional-live-order-count", type=int, default=0)
    parser.add_argument("--additional-network-submit-count", type=int, default=0)
    parser.add_argument("--additional-exchange-submit-count", type=int, default=0)
    parser.add_argument("--max-abs-slippage-pct", type=float, default=2.5)
    parser.add_argument("--max-abs-unrealized-pnl-pct", type=float, default=5.0)
    parser.add_argument("--operator-notes", default=None)
    args = parser.parse_args()

    if args.source_30y_report:
        source_path = Path(args.source_30y_report)
        payload = build_post_live_micro_canary_risk_review_snapshot(
            load_json(source_path),
            source_report_path=source_path,
            fee_amount=args.fee_amount,
            fee_asset=args.fee_asset,
            review_mark_price=args.review_mark_price,
            reference_price=args.reference_price,
            emergency_stop_armed=args.emergency_stop_armed,
            kill_switch_armed=not args.kill_switch_not_armed,
            additional_live_order_count=args.additional_live_order_count,
            additional_network_submit_count=args.additional_network_submit_count,
            additional_exchange_submit_count=args.additional_exchange_submit_count,
            max_abs_slippage_pct_allowed=args.max_abs_slippage_pct,
            max_abs_unrealized_pnl_pct_allowed=args.max_abs_unrealized_pnl_pct,
            operator_notes=args.operator_notes,
        )
    else:
        payload = build_from_latest_30y_h1_reconciliation(
            args.reports_dir,
            fee_amount=args.fee_amount,
            fee_asset=args.fee_asset,
            review_mark_price=args.review_mark_price,
            reference_price=args.reference_price,
            emergency_stop_armed=args.emergency_stop_armed,
            kill_switch_armed=not args.kill_switch_not_armed,
            additional_live_order_count=args.additional_live_order_count,
            additional_network_submit_count=args.additional_network_submit_count,
            additional_exchange_submit_count=args.additional_exchange_submit_count,
            max_abs_slippage_pct_allowed=args.max_abs_slippage_pct,
            max_abs_unrealized_pnl_pct_allowed=args.max_abs_unrealized_pnl_pct,
            operator_notes=args.operator_notes,
        )

    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    print(json.dumps({
        "ok": bool(payload.get("approved_for_post_live_micro_canary_risk_review")),
        "contract_version": payload.get("contract_version"),
        "decision": payload.get("decision"),
        "json_path": str(json_path),
        "md_path": str(md_path),
        "source_30y_h1_reconciliation_verified": payload.get("source_30y_h1_reconciliation_verified"),
        "real_fill_risk_review_verified": payload.get("real_fill_risk_review_verified"),
        "pnl_evidence_verified": payload.get("pnl_evidence_verified"),
        "fee_evidence_verified": payload.get("fee_evidence_verified"),
        "slippage_evidence_verified": payload.get("slippage_evidence_verified"),
        "emergency_stop_continuity_verified": payload.get("emergency_stop_continuity_verified"),
        "no_additional_live_order_verified": payload.get("no_additional_live_order_verified"),
        "additional_live_order_count": payload.get("additional_live_order_count"),
        "patch_network_submit_attempted": payload.get("patch_network_submit_attempted"),
        "patch_exchange_submit_performed": payload.get("patch_exchange_submit_performed"),
        "approved_for_additional_live_order": payload.get("approved_for_additional_live_order"),
        "reason_codes": payload.get("reason_codes"),
    }, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
