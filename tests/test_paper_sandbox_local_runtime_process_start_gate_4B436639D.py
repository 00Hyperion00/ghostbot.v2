from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_local_runtime_process_start_gate import (
    READY_DECISION,
    REQUIRED_AUTHORIZATION_PHRASE,
    REQUIRED_SOURCE_FLAGS,
    build_report,
    find_latest_source_report,
)


def write_source_report(reports_dir: Path, *, overrides: dict[str, object] | None = None, name_suffix: str = "ready") -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    sample = {
        "approval_phrase": REQUIRED_AUTHORIZATION_PHRASE,
        "approval_scope": "paper_sandbox_runtime_start_authorization_ledger_review_only",
        "approved_at_utc": "20260706T000000Z",
        "operator_id": "op.local",
        "operator_name": "Operator Local",
        "operator_role": "paper_sandbox_runtime_start_authorizer",
        "source_report": "reports/recovery/4B436639B_paper_sandbox_runtime_start_command_contract_20260706T000000Z_ready.json",
        "runtime_start_allowed": False,
        "runtime_start_command_executed": False,
        "network_order_submit_allowed": False,
    }
    schema = {
        "approval_phrase_required": REQUIRED_AUTHORIZATION_PHRASE,
        "approval_scope_required": "paper_sandbox_runtime_start_authorization_ledger_review_only",
    }
    payload = dict(REQUIRED_SOURCE_FLAGS)
    payload.update(
        {
            "runtime_start_command_template": "python -m tradebot.paper_runtime_entry --mode paper-sandbox --config config/paper_sandbox.runtime.json --runtime-lock runtime/paper_sandbox_runtime.lock --no-network-order --no-live --no-exchange-submit",
            "runtime_start_operator_authorization_valid_evidence_sample": sample,
            "approval_evidence_schema": schema,
            "final_safety_violations": [],
        }
    )
    if overrides:
        payload.update(overrides)
    path = reports_dir / f"4B436639C_paper_sandbox_runtime_start_authorization_ledger_20260706T000000Z_{name_suffix}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_ready_report_from_valid_39c_source(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    source = write_source_report(reports)
    report = build_report(reports)
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_39c_report"] == str(source)
    assert report["source_39c_status"] == "SOURCE_39C_READY"
    assert report["final_safety_violation_count"] == 0


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    report = build_report(tmp_path / "reports" / "recovery")
    assert report["status"] == "NOT_READY"
    assert report["ok"] is False
    assert report["source_39c_status"] == "SOURCE_39C_MISSING"
    assert report["runtime_start_command_executed"] is False
    assert report["network_order_submit_performed"] is False


def test_invalid_authorization_evidence_fails_closed(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports, overrides={"runtime_start_operator_authorization_valid_evidence_sample": {"approval_phrase": "BAD"}})
    report = build_report(reports)
    assert report["status"] == "NOT_READY"
    assert report["explicit_authorization_evidence_validation_ready"] is False
    assert report["runtime_start_command_executed"] is False


def test_latest_main_ready_report_selection_ignores_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    main = write_source_report(reports)
    artifact = reports / "4B436639C_runtime_start_authorization_ledger_probe_20260706T000001Z.json"
    artifact.write_text(json.dumps({"status": "READY"}), encoding="utf-8")
    selected = find_latest_source_report(reports)
    assert selected == main


def test_gate_contract_is_review_only_and_not_execution(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["local_runtime_process_start_gate_ready"] is True
    assert report["local_runtime_process_start_gate_review_only"] is True
    assert report["local_runtime_process_start_gate_approval_required"] is True
    assert report["local_runtime_process_start_gate_approval_performed"] is False
    assert report["local_runtime_process_start_gate_approved_for_command_execution"] is False
    assert report["local_runtime_process_start_gate_contract_rule_count"] == 14
    assert report["local_runtime_process_start_gate_contract_ready_count"] == 14


def test_authorization_evidence_validation_fields(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["explicit_authorization_evidence_validation_complete"] is True
    assert report["explicit_authorization_evidence_validation_ready"] is True
    assert report["authorization_phrase_validated"] is True
    assert report["authorization_source_reference_validated"] is True
    assert report["operator_identity_validated"] is True
    assert report["operator_approval_timestamp_validated"] is True
    assert report["authorization_review_only_lock_validated"] is True


def test_probe_counts_are_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["paper_sandbox_local_runtime_process_start_gate_probe_count"] == 22
    assert report["paper_sandbox_local_runtime_process_start_gate_probe_passed_count"] == 22
    assert report["paper_sandbox_local_runtime_process_start_gate_check_count"] == 31
    assert report["paper_sandbox_local_runtime_process_start_gate_ready_count"] == 31


def test_runtime_network_live_exchange_remain_locked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["runtime_start_command_execution_allowed"] is False
    assert report["runtime_start_command_executed"] is False
    assert report["runtime_process_started"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["runtime_health_probe_performed"] is False
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False


def test_write_artifacts_creates_ready_report(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports, write_artifacts=True)
    assert report["status"] == "READY"
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert Path(report["local_runtime_process_start_gate_contract_path"]).exists()
    assert Path(report["explicit_authorization_evidence_validation_path"]).exists()


def test_next_phase_not_auto_unlocked(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_source_report(reports)
    report = build_report(reports)
    assert report["next_phase"] == "4B.4.3.6.6.39E"
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False
