from __future__ import annotations

import json
from pathlib import Path

from tradebot.second_micro_canary_submit_gate import (
    FINALIZATION_TOKEN,
    OPERATOR_APPROVAL_REQUIRED_DECISION,
    READY_DECISION,
    SIZING_REQUIRED_DECISION,
    SOURCE_32A_CONTRACT_VERSION,
    SOURCE_32A_READY_DECISION,
    build_from_explicit_32a_report,
    build_from_latest_32a_report,
    evaluate_min_notional_sizing,
    evaluate_source_32a_release_candidate,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _source_32a() -> dict[str, object]:
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


def test_source_32a_requires_ready_and_no_submit() -> None:
    status = evaluate_source_32a_release_candidate(_source_32a())
    assert status.ok is True
    broken = dict(_source_32a())
    broken["approved_for_live_real_order"] = True
    assert evaluate_source_32a_release_candidate(broken).ok is False


def test_min_notional_sizing_rounds_qty_and_stays_under_cap() -> None:
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
    assert sizing.ok is True
    assert sizing.candidate_quantity == "0.0029"
    assert sizing.candidate_notional_usdt is not None
    assert sizing.candidate_notional_usdt <= 5


def test_min_notional_sizing_fails_closed_if_rounding_exceeds_cap() -> None:
    sizing = evaluate_min_notional_sizing(
        symbol="ETHUSDT",
        side="BUY",
        order_type="MARKET",
        reference_price=1713.36,
        requested_notional_usdt=5,
        exchange_min_notional_usdt="5",
        quantity_step="0.0001",
        min_quantity="0.0001",
        capital_cap_usdt=25,
        second_micro_max_notional_usdt=5,
        daily_loss_limit_usdt=5,
        max_slippage_bps=50,
    )
    assert sizing.ok is False
    assert "CANDIDATE_NOTIONAL_EXCEEDS_SECOND_MICRO_CAP_FAIL_CLOSED" in sizing.reason_codes


def test_ready_submit_gate_creates_evidence_only_request(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
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
        audit_comment="unit test",
        symbol="ETHUSDT",
        side="BUY",
        order_type="MARKET",
        reference_price=1713.36,
        requested_notional_usdt=4.95,
        exchange_min_notional_usdt="4.95",
        quantity_step="0.0001",
        min_quantity="0.0001",
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_submit_request_evidence"] is True
    assert payload["submit_request_evidence_created"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real_order"] is False
    assert payload["approved_for_second_micro_canary_order_submit"] is False
    assert payload["patch_network_submit_attempted"] is False
    assert payload["submit_request"]["must_not_be_submitted_by_32b"] is True


def test_operator_approval_required_by_default(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436632A_post_freeze_release_candidate_review_20260622T121500Z_ready.json"
    _write_json(source, _source_32a())
    payload = build_from_explicit_32a_report(
        reports_dir=reports,
        source_32a_report=source,
        operator_id="operator-32b",
        finalization_token=FINALIZATION_TOKEN,
        emergency_stop_armed=True,
        operator_approve_submit_request=False,
        operator_approval_id=None,
        reference_price=1713.36,
        requested_notional_usdt=4.95,
        exchange_min_notional_usdt="4.95",
    )
    assert payload["decision"] == OPERATOR_APPROVAL_REQUIRED_DECISION
    assert payload["submit_request_evidence_created"] is False
    assert payload["approved_for_exchange_submit"] is False


def test_latest_source_discovery_and_report_bundle(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436632A_post_freeze_release_candidate_review_20260622T121500Z_ready.json"
    _write_json(source, _source_32a())
    payload = build_from_latest_32a_report(
        reports_dir=reports,
        operator_id="operator-32b",
        finalization_token=FINALIZATION_TOKEN,
        emergency_stop_armed=True,
        operator_approve_submit_request=True,
        operator_approval_id="OPERATOR_APPROVES_32B_SUBMIT_REQUEST_ONLY",
        reference_price=1713.36,
        requested_notional_usdt=4.95,
        exchange_min_notional_usdt="4.95",
    )
    json_path, md_path = write_report_bundle(payload, reports_dir=reports)
    assert payload["decision"] == READY_DECISION
    assert json_path.exists()
    assert md_path.exists()
    stored = json.loads(json_path.read_text(encoding="utf-8"))
    assert stored["submit_request_evidence_created"] is True


def test_sizing_failure_blocks_submit_request(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
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
        reference_price=1713.36,
        requested_notional_usdt=5,
        exchange_min_notional_usdt="5",
    )
    assert payload["decision"] == SIZING_REQUIRED_DECISION
    assert payload["submit_request"] is None
    assert payload["approved_for_exchange_submit"] is False
