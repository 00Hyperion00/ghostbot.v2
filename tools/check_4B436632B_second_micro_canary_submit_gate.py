from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from tradebot.second_micro_canary_submit_gate import (
    CONTRACT_VERSION,
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_32A_CONTRACT_VERSION,
    SOURCE_32A_READY_DECISION,
    build_from_explicit_32a_report,
    evaluate_min_notional_sizing,
    evaluate_source_32a_release_candidate,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _source_32a() -> dict[str, Any]:
    return {
        "contract_version": SOURCE_32A_CONTRACT_VERSION,
        "decision": SOURCE_32A_READY_DECISION,
        "source_31b_release_hygiene_verified": True,
        "final_audit_snapshot_reviewed": True,
        "capital_cap_confirmed": True,
        "capital_cap_usdt": 25,
        "second_micro_canary_eligible_candidate": True,
        "second_micro_max_notional_usdt": 5,
        "daily_loss_limit_usdt": 5,
        "max_slippage_bps": 50,
        "emergency_stop_armed_verified": True,
        "approved_for_live_real_order": False,
        "approved_for_second_micro_canary_order_submit": False,
        "approved_for_exchange_submit": False,
        "approved_for_additional_exchange_submit": False,
        "patch_network_submit_attempted": False,
        "patch_exchange_submit_performed": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
    }


def run_checks() -> dict[str, Any]:
    source_status = evaluate_source_32a_release_candidate(_source_32a())
    sizing = evaluate_min_notional_sizing(
        symbol="ETHUSDT",
        side="BUY",
        order_type="MARKET",
        reference_price=1713.36,
        requested_notional_usdt=4.95,
        exchange_min_notional_usdt="4.95",
        quantity_step="0.0001",
        min_quantity="0.0001",
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    cap_block = evaluate_min_notional_sizing(
        symbol="ETHUSDT",
        side="BUY",
        order_type="MARKET",
        reference_price=1713.36,
        requested_notional_usdt=5.0,
        exchange_min_notional_usdt="5.0",
        quantity_step="0.0001",
        min_quantity="0.0001",
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    with tempfile.TemporaryDirectory() as tmp:
        reports = Path(tmp) / "reports" / "production_hardening"
        source = reports / "4B436632A_post_freeze_release_candidate_review_20260622T121500Z_ready.json"
        _write_json(source, _source_32a())
        payload = build_from_explicit_32a_report(
            reports_dir=reports,
            source_32a_report=source,
            operator_id="operator-32b",
            finalization_token=FINALIZATION_TOKEN,
            emergency_stop_armed=True,
            operator_approve_submit_request=True,
            operator_approval_id="OPERATOR_APPROVES_32B_SUBMIT_REQUEST_ONLY",
            audit_comment="checker",
            symbol="ETHUSDT",
            side="BUY",
            order_type="MARKET",
            reference_price=1713.36,
            requested_notional_usdt=4.95,
            exchange_min_notional_usdt="4.95",
            quantity_step="0.0001",
            min_quantity="0.0001",
        )
        json_path, md_path = write_report_bundle(payload, reports_dir=reports)
        report_written = json_path.exists() and md_path.exists()
    checks = {
        "contract_version_ok": CONTRACT_VERSION == "4B.4.3.6.6.32B",
        "source_32a_verified": source_status.ok,
        "sizing_ready_under_cap": sizing.ok,
        "sizing_fail_closed_when_rounding_exceeds_cap": not cap_block.ok and "CANDIDATE_NOTIONAL_EXCEEDS_SECOND_MICRO_CAP_FAIL_CLOSED" in cap_block.reason_codes,
        "ready_decision_ok": payload.get("decision") == READY_DECISION,
        "submit_request_evidence_created": payload.get("submit_request_evidence_created") is True,
        "exchange_submit_false": payload.get("approved_for_exchange_submit") is False,
        "live_order_false": payload.get("approved_for_live_real_order") is False,
        "second_micro_order_submit_false": payload.get("approved_for_second_micro_canary_order_submit") is False,
        "patch_network_submit_false": payload.get("patch_network_submit_attempted") is False,
        "report_written": report_written,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "candidate_quantity": payload.get("candidate_quantity"),
        "candidate_estimated_notional_usdt": payload.get("candidate_estimated_notional_usdt"),
        "decision": payload.get("decision"),
        "cap_block_reason_codes": cap_block.reason_codes,
        "approved_for_exchange_submit": False,
        "approved_for_live_real_order": False,
        "patch_network_submit_attempted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.32B second micro-canary submit gate checker")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = run_checks()
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
