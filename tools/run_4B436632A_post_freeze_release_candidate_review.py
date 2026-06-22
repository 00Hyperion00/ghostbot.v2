from __future__ import annotations

import argparse
import json
from typing import Any

from tradebot.post_freeze_release_candidate_review import (
    DEFAULT_REPORTS_DIR,
    READY_DECISION,
    build_from_explicit_31b_report,
    build_from_latest_31b_report,
    write_report_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.32A post-freeze release candidate review runner")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--source-31b-report", default=None, help="Explicit accepted 31B READY JSON report path")
    parser.add_argument("--operator-id", default=None)
    parser.add_argument("--finalization-token", default=None)
    parser.add_argument("--audit-comment", default=None)
    parser.add_argument("--emergency-stop-armed", action="store_true")
    parser.add_argument("--capital-cap-usdt", default=None)
    parser.add_argument("--second-micro-max-notional-usdt", default=None)
    parser.add_argument("--daily-loss-limit-usdt", default=None)
    parser.add_argument("--max-slippage-bps", default=None)
    parser.add_argument("--once-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kwargs: dict[str, Any] = {
        "reports_dir": args.reports_dir,
        "operator_id": args.operator_id,
        "finalization_token": args.finalization_token,
        "audit_comment": args.audit_comment,
        "emergency_stop_armed": args.emergency_stop_armed,
        "capital_cap_usdt": args.capital_cap_usdt,
        "second_micro_max_notional_usdt": args.second_micro_max_notional_usdt,
        "daily_loss_limit_usdt": args.daily_loss_limit_usdt,
        "max_slippage_bps": args.max_slippage_bps,
    }
    if args.source_31b_report:
        payload = build_from_explicit_31b_report(source_31b_report=args.source_31b_report, **kwargs)
    else:
        payload = build_from_latest_31b_report(**kwargs)
    json_path, md_path = write_report_bundle(payload, reports_dir=args.reports_dir)
    output: dict[str, Any] = {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "contract_version": payload.get("contract_version"),
        "report_path": str(json_path),
        "markdown_path": str(md_path),
        "source_31b_release_hygiene_verified": payload.get("source_31b_release_hygiene_verified"),
        "final_audit_snapshot_reviewed": payload.get("final_audit_snapshot_reviewed"),
        "live_real_continuation_risk_decision": payload.get("live_real_continuation_risk_decision"),
        "capital_cap_confirmed": payload.get("capital_cap_confirmed"),
        "capital_cap_usdt": payload.get("capital_cap_usdt"),
        "second_micro_canary_eligible_candidate": payload.get("second_micro_canary_eligible_candidate"),
        "second_micro_max_notional_usdt": payload.get("second_micro_max_notional_usdt"),
        "daily_loss_limit_usdt": payload.get("daily_loss_limit_usdt"),
        "max_slippage_bps": payload.get("max_slippage_bps"),
        "emergency_stop_armed_verified": payload.get("emergency_stop_armed_verified"),
        "approved_for_live_real_order": payload.get("approved_for_live_real_order"),
        "approved_for_second_micro_canary_order_submit": payload.get("approved_for_second_micro_canary_order_submit"),
        "patch_network_submit_attempted": payload.get("patch_network_submit_attempted"),
        "additional_live_real_order_performed": payload.get("additional_live_real_order_performed"),
        "reason_codes": payload.get("reason_codes", []),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if output["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
