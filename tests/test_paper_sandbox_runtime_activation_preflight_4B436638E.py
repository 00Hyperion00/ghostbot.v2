from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_sandbox_runtime_activation_preflight import (
    READY_DECISION,
    SOURCE_READY_DECISION_38D,
    build_report,
)


def _write_source_38d(root: Path) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "4B436638D_paper_sandbox_operator_approval_ledger_20260705T123038Z_ready.json"
    payload = {
        "patch_id": "4B436638D",
        "patch_version": "4B.4.3.6.6.38D",
        "patch_name": "Paper Sandbox Operator Approval Ledger",
        "status": "READY",
        "decision": SOURCE_READY_DECISION_38D,
        "operator_approval_ledger_locked": True,
        "operator_approval_ledger_ready": True,
        "paper_sandbox_operator_approval_ledger_ready": True,
        "valid_operator_approval_ledger_runtime_denied_no_submit": True,
        "valid_operator_approval_ledger_network_order_denied": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "phase_38_planning_only": True,
        "paper_transition_blocked": True,
        "paper_runtime_start_performed": False,
        "runtime_start_performed": False,
        "network_order_submit_performed": False,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_38e_ready_source_gate_and_decision(tmp_path: Path) -> None:
    source = _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_38d_status"] == "SOURCE_38D_READY"
    assert report["source_38d_report"] == str(source)


def test_typed_operator_approval_verification_locked(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["typed_operator_approval_verification_complete"] is True
    assert report["typed_operator_approval_verification_locked"] is True
    assert report["typed_runtime_activation_approval_required"] is True
    assert report["typed_operator_approval_phrase_required"] == "APPROVE PAPER SANDBOX RUNTIME ACTIVATION PREFLIGHT ONLY"
    assert report["operator_identity_required"] is True
    assert report["operator_id_required"] is True
    assert report["operator_name_required"] is True
    assert report["operator_role_required"] is True
    assert report["operator_approval_timestamp_required"] is True
    assert report["source_report_required"] is True


def test_local_runtime_start_preflight_no_start(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["local_runtime_start_preflight_complete"] is True
    assert report["local_runtime_start_preflight_locked"] is True
    assert report["runtime_process_lock_required"] is True
    assert report["single_instance_runtime_required"] is True
    assert report["runtime_start_command_template_declared"] is True
    assert report["runtime_start_command_executed"] is False
    assert report["paper_runtime_start_performed"] is False
    assert report["runtime_start_performed"] is False


def test_activation_probe_fail_closed_and_review_only(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["runtime_activation_preflight_probe_complete"] is True
    assert report["runtime_activation_preflight_probe_count"] == 14
    assert report["runtime_activation_preflight_probe_passed_count"] == 14
    assert report["typed_activation_approval_missing_denied"] is True
    assert report["typed_activation_approval_invalid_denied"] is True
    assert report["operator_identity_missing_denied"] is True
    assert report["valid_activation_preflight_approval_accepted_for_review"] is True
    assert report["valid_activation_preflight_approval_runtime_denied_no_submit"] is True
    assert report["valid_activation_preflight_approval_network_order_denied"] is True


def test_no_network_order_no_live_no_exchange_submit(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["no_network_order_no_live_no_exchange_submit_guard_complete"] is True
    assert report["network_order_submit_allowed"] is False
    assert report["network_order_submit_performed"] is False
    assert report["approved_for_live_real"] is False
    assert report["live_environment_enabled"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_performed"] is False
    assert report["network_request_performed"] is False
    assert report["signed_request_performed"] is False
    assert report["private_api_access_allowed"] is False


def test_gate_counts_and_next_phase_locked(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    report = build_report(tmp_path)
    assert report["paper_sandbox_runtime_activation_preflight_gate_complete"] is True
    assert report["paper_sandbox_runtime_activation_preflight_gate_check_count"] == 36
    assert report["paper_sandbox_runtime_activation_preflight_gate_ready_count"] == 36
    assert report["next_phase"] == "4B.4.3.6.6.38F"
    assert report["next_phase_unlock_allowed"] is False
    assert report["transition_to_next_phase_performed"] is False


def test_missing_source_not_ready(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_38d_status"] == "SOURCE_38D_NOT_FOUND"
    assert report["decision"] != READY_DECISION


def test_write_reports_creates_terminal_and_components(tmp_path: Path) -> None:
    _write_source_38d(tmp_path)
    reports = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, reports_dir=reports, write_reports=True)
    assert report["ok"] is True
    assert Path(report["report_path"]).exists()
    assert Path(report["typed_operator_approval_verification_path"]).exists()
    assert Path(report["local_runtime_start_preflight_path"]).exists()
    assert Path(report["runtime_activation_preflight_probe_path"]).exists()
    assert Path(report["paper_sandbox_runtime_activation_preflight_gate_path"]).exists()
