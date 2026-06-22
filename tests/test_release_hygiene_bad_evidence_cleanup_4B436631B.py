from __future__ import annotations

import json
from pathlib import Path

from tradebot.release_hygiene_bad_evidence_cleanup import (
    FINALIZATION_TOKEN,
    READY_DECISION,
    SOURCE_31A_H3_CONTRACT_VERSION,
    SOURCE_31A_H3_READY_DECISION,
    build_from_explicit_31a_h3_report,
    build_from_latest_31a_h3_report,
    evaluate_source_31a_h3_closure,
    write_report_bundle,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _source() -> dict[str, object]:
    return {
        "contract_version": SOURCE_31A_H3_CONTRACT_VERSION,
        "decision": SOURCE_31A_H3_READY_DECISION,
        "source_30z_risk_review_verified": True,
        "evidence_pack_sealed": True,
        "release_hygiene_verified": True,
        "operator_audit_finalized": True,
        "no_further_live_orders_verified": True,
        "emergency_stop_continuity_verified": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_network_submit_attempted": False,
        "patch_exchange_submit_performed": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
        "evidence_pack_file_count": 15,
    }


def test_source_31a_h3_requires_ready_contract_and_no_live_submit() -> None:
    status = evaluate_source_31a_h3_closure(_source())
    assert status.ok is True
    assert status.patch_network_submit_attempted is False
    broken = dict(_source())
    broken["patch_network_submit_attempted"] = True
    assert evaluate_source_31a_h3_closure(broken).ok is False


def test_ready_run_moves_bad_not_ready_artifacts_to_quarantine(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T094041Z_ready.json"
    _write_json(source, _source())
    bad_json = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T081900Z_not_ready.json"
    bad_md = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T081900Z_not_ready.md"
    _write_json(bad_json, {"contract_version": "4B.4.3.6.6.31A", "decision": "NOT_READY"})
    bad_md.write_text("# bad\n", encoding="utf-8")
    payload = build_from_explicit_31a_h3_report(
        reports_dir=reports,
        source_31a_h3_report=source,
        operator_id="operator-31b",
        finalization_token=FINALIZATION_TOKEN,
        audit_comment="unit test",
        move_bad_evidence_to_quarantine=True,
        quarantine_manifest_id="UNIT_TEST_QUARANTINE",
    )
    assert payload["decision"] == READY_DECISION
    assert payload["source_31a_h3_freeze_audit_closure_verified"] is True
    assert payload["bad_evidence_history_explained"] is True
    assert payload["bad_evidence_quarantined"] is True
    assert payload["bad_evidence_quarantine_moved_file_count"] == 2
    assert payload["bad_evidence_quarantine_remaining_file_count"] == 0
    assert payload["patch_network_submit_attempted"] is False
    assert not bad_json.exists()
    assert not bad_md.exists()
    quarantine_files = list((reports / "quarantine").rglob("*not_ready.*"))
    assert len(quarantine_files) == 2


def test_latest_source_discovery_and_report_bundle(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T094041Z_ready.json"
    _write_json(source, _source())
    payload = build_from_latest_31a_h3_report(
        reports_dir=reports,
        operator_id="operator-31b",
        finalization_token=FINALIZATION_TOKEN,
        audit_comment="latest discovery",
        move_bad_evidence_to_quarantine=True,
    )
    json_path, md_path, manifest_path = write_report_bundle(payload, reports_dir=reports)
    assert payload["decision"] == READY_DECISION
    assert json_path.exists()
    assert md_path.exists()
    assert manifest_path.exists()
    stored = json.loads(json_path.read_text(encoding="utf-8"))
    assert stored["quarantine_manifest_path"].endswith("_quarantine_manifest.json")


def test_missing_operator_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "production_hardening"
    source = reports / "4B436631A_live_micro_canary_freeze_audit_closure_20260622T094041Z_ready.json"
    _write_json(source, _source())
    payload = build_from_explicit_31a_h3_report(
        reports_dir=reports,
        source_31a_h3_report=source,
        operator_id=None,
        finalization_token=FINALIZATION_TOKEN,
        move_bad_evidence_to_quarantine=True,
    )
    assert payload["decision"] != READY_DECISION
    assert "OPERATOR_ID_REQUIRED" in payload["reason_codes"]
