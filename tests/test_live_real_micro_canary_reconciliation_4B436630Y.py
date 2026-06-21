from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.live_real_micro_canary_reconciliation import (
    EXECUTION_EVIDENCE_REQUIRED_DECISION,
    MISMATCH_DECISION,
    READY_DECISION,
    build_from_latest_30x_report_and_request,
    build_live_real_micro_canary_reconciliation_snapshot,
    build_manual_execution_evidence,
    evaluate_source_30x_submit_request,
    latest_valid_30x_report_and_request,
    write_report_bundle,
)


def source_30x() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30X",
        "decision": "FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT",
        "approved_for_first_live_real_micro_canary_gate": True,
        "approved_for_manual_runtime_handoff": True,
        "approved_for_exchange_submit": True,
        "approved_for_live_real": True,
        "automated_network_submit_disabled_verified": True,
        "submit_request_built": True,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
    }


def request_30x() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30X",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.002,
        "mark_price_reference": 2500.0,
        "notional_usd_reference": 5.0,
        "client_order_id": "tbv2-30x-test",
    }


def test_default_requires_execution_evidence_but_patch_does_not_submit() -> None:
    payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source_30x(), request_30x(), {})
    assert payload["decision"] == EXECUTION_EVIDENCE_REQUIRED_DECISION
    assert payload["source_30x_submit_request_verified"] is True
    assert payload["execution_evidence_verified"] is False
    assert payload["patch_network_submit_attempted"] is False
    assert payload["approved_for_additional_exchange_submit"] is False


def test_ready_reconciliation_mismatch_zero_and_emergency_stop_armed() -> None:
    status = evaluate_source_30x_submit_request(source_30x(), request_30x())
    evidence = build_manual_execution_evidence(status, operator_id="operator-30y", exchange_order_id="EX-30Y-1", ledger_event_id="LEDGER-30Y-1")
    payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source_30x(), request_30x(), evidence)
    assert payload["decision"] == READY_DECISION
    assert payload["mismatch_count"] == 0
    assert payload["mismatch_zero_verified"] is True
    assert payload["emergency_stop_armed_verified"] is True
    assert payload["external_exchange_submit_performed"] is True
    assert payload["patch_network_submit_attempted"] is False
    assert payload["approved_for_live_real_continuation"] is False


def test_mismatch_detected_when_quantity_does_not_match() -> None:
    status = evaluate_source_30x_submit_request(source_30x(), request_30x())
    evidence = build_manual_execution_evidence(status, operator_id="operator-30y", exchange_order_id="EX-30Y-2", filled_quantity="0.003", ledger_filled_quantity="0.003", ledger_notional_usd="7.5", account_position_delta_qty="0.003")
    payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source_30x(), request_30x(), evidence)
    assert payload["decision"] == MISMATCH_DECISION
    assert payload["mismatch_count"] >= 1
    assert "QUANTITY_MISMATCH" in payload["reason_codes"]


def test_latest_valid_30x_and_bundle_round_trip(tmp_path: Path) -> None:
    src = source_30x()
    req = request_30x()
    req_path = tmp_path / "4B436630X_first_live_real_micro_canary_submit_request.json"
    req_path.write_text(__import__("json").dumps(req), encoding="utf-8")
    src["submit_request_path"] = str(req_path)
    src_path = tmp_path / "4B436630X_first_live_real_micro_canary_20260621T000000Z_ready.json"
    src_path.write_text(__import__("json").dumps(src), encoding="utf-8")
    selected_source, selected_payload, selected_request, request_payload = latest_valid_30x_report_and_request(tmp_path)
    assert selected_source == src_path
    assert selected_request == req_path
    assert selected_payload["contract_version"] == "4B.4.3.6.6.30X"
    status = evaluate_source_30x_submit_request(selected_payload, request_payload)
    evidence = build_manual_execution_evidence(status, operator_id="operator-30y", exchange_order_id="EX-30Y-3")
    built = build_live_real_micro_canary_reconciliation_snapshot(Settings(), selected_payload, request_payload, evidence)
    json_path, md_path = write_report_bundle(built, tmp_path)
    assert json_path.exists()
    assert md_path.exists()


def test_build_from_latest_can_emit_ready_with_operator_execution(tmp_path: Path) -> None:
    src = source_30x()
    req = request_30x()
    req_path = tmp_path / "4B436630X_first_live_real_micro_canary_submit_request.json"
    req_path.write_text(__import__("json").dumps(req), encoding="utf-8")
    src["submit_request_path"] = str(req_path)
    (tmp_path / "4B436630X_first_live_real_micro_canary_20260621T000001Z_ready.json").write_text(__import__("json").dumps(src), encoding="utf-8")
    payload = build_from_latest_30x_report_and_request(Settings(), tmp_path, operator_executed=True, operator_id="operator-30y", exchange_order_id="EX-30Y-4")
    assert payload["decision"] == READY_DECISION
    assert payload["mismatch_count"] == 0
