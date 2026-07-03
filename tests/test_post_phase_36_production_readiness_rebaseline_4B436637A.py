from __future__ import annotations

import json
from pathlib import Path

from tradebot.post_phase_36_production_readiness_rebaseline import evaluate_post_phase_36_production_readiness_rebaseline


def _write_source_36g(root: Path, *, ready: bool = True, safety_violation: bool = False, phase36_final: bool = True) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_FINAL_CLOSURE_READY_NO_SUBMIT_PHASE_36_FINAL_SEALED",
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_interim_closed": True,
        "phase_36_final_closed": phase36_final,
        "no_submit_phase_36_final_closed": phase36_final,
        "public_observation_final_closure_ready": True,
        "public_observation_final_sealed": True,
        "phase_36_remote_tag_audit_complete": True,
        "phase_36_missing_remote_tag_count": 0,
        "no_submit_phase_36_final_seal_digest": "seal-digest",
        "phase_36_remote_tag_audit_digest": "remote-tag-digest",
        "source_36f_gate_digest": "source-gate-digest",
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "evidence_collection_started": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "http_request_performed": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "network_request_allowed_now": False,
        "network_request_performed": safety_violation,
        "network_submit_allowed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_consumed": False,
        "operator_observation_token_validated": False,
        "order_submit_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_data_fetch_adapter_executed": False,
        "public_market_data_collection_performed": False,
        "public_observation_dry_run_collector_executed": False,
        "public_observation_execution_performed": False,
        "public_observation_network_off_execution_package_executed": False,
        "reload_performed": False,
        "report_delete_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_evidence_collection_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "signed_request_performed": False,
        "simulated_approval_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    path = reports / "4B436636G_public_observation_final_closure_20260703T121628Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_36g_final_closure_is_ready(tmp_path: Path) -> None:
    _write_source_36g(tmp_path)
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36g_complete"] is True
    assert result["closed_phase_carryforward_complete"] is True
    assert result["closed_phase_carryforward_closed_count"] == 3
    assert result["p0_hardening_gap_matrix_complete"] is True
    assert result["p0_hardening_gap_count"] == 10
    assert result["p0_hardening_open_gap_count"] == 10
    assert result["p0_hardening_closed_gap_count"] == 0
    assert result["p0_hardening_complete"] is False
    assert result["no_submit_37a_planning_gate_complete"] is True
    assert result["no_submit_37a_planning_gate_ready_count"] == 9
    assert result["phase_37_planning_only"] is True
    assert result["phase_37_unlocked"] is False
    assert result["network_request_performed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_blocked"] is True


def test_not_ready_when_source_36g_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36g_complete"] is False
    assert result["closed_phase_carryforward_complete"] is False
    assert result["p0_hardening_gap_matrix_complete"] is False
    assert result["no_submit_37a_planning_gate_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_36g_final_closure_missing(tmp_path: Path) -> None:
    _write_source_36g(tmp_path, phase36_final=False)
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36g_complete"] is False
    assert result["phase_36_final_closed"] is False
    assert result["p0_hardening_performed"] is False
    assert result["phase_37_execution_started"] is False


def test_not_ready_when_source_36g_has_safety_violation(tmp_path: Path) -> None:
    _write_source_36g(tmp_path, safety_violation=True)
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36g_complete"] is False
    assert result["source_36g_safety_violation_count"] == 1
    assert "network_request_performed" in result["source_36g_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["exchange_submit_performed"] is False
    assert result["p0_hardening_performed"] is False
