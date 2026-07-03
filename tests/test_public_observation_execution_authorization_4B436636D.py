from __future__ import annotations

import json
from pathlib import Path

from tradebot.public_observation_execution_authorization import evaluate_public_observation_execution_authorization


def _write_source_36c(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_READY_NO_SUBMIT_RUNTIME_EVIDENCE_GUARD_LOCKED",
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "source_36b_complete": True,
        "read_only_public_data_fetch_adapter_complete": True,
        "read_only_public_data_fetch_adapter_locked": True,
        "read_only_public_data_fetch_adapter_digest": "adapter-digest",
        "observation_artifact_writer_complete": True,
        "observation_artifact_writer_locked": True,
        "observation_artifact_writer_digest": "writer-digest",
        "no_submit_runtime_evidence_guard_complete": True,
        "no_submit_runtime_evidence_guard_locked": True,
        "no_submit_runtime_evidence_guard_digest": "guard-digest",
        "public_observation_dry_run_collector_ready": True,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_READY_PLANNING_ONLY_NO_SUBMIT",
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "runtime_evidence_artifact_written": False,
        "public_market_data_collection_performed": safety_violation,
        "public_observation_execution_performed": False,
        "public_observation_dry_run_collector_executable_now": False,
        "public_observation_dry_run_collector_executed": False,
        "public_data_fetch_adapter_executed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "destructive_cleanup_performed": False,
        "deduplication_action_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "paper_transition_approval_performed": False,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "public_data_collection_allowed_now": False,
        "public_data_observation_allowed_now": False,
        "public_endpoint_execution_allowed_now": False,
        "public_observation_execution_allowed_now": False,
        "observation_artifact_written": False,
        "observation_artifact_validation_performed": False,
        "read_only_public_data_fetch_adapter_relaxed": False,
        "observation_artifact_writer_relaxed": False,
        "no_submit_runtime_evidence_guard_relaxed": False,
    }
    path = reports / "4B436636C_public_observation_dry_run_collector_20260703T115002Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36c_is_guarded_collector_ready(tmp_path: Path) -> None:
    _write_source_36c(tmp_path)
    result = evaluate_public_observation_execution_authorization(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36c_complete"] is True
    assert result["operator_observation_token_ledger_complete"] is True
    assert result["operator_observation_token_template_complete"] is True
    assert result["operator_observation_token_present"] is False
    assert result["operator_observation_authorization_unlocked"] is False
    assert result["network_off_safety_override_ledger_complete"] is True
    assert result["network_off_safety_override_locked"] is True
    assert result["network_request_allowed_now"] is False
    assert result["network_request_performed"] is False
    assert result["no_submit_execution_seal_complete"] is True
    assert result["no_submit_execution_seal_locked"] is True
    assert result["public_observation_execution_authorization_ready"] is True
    assert result["public_observation_execution_authorized_now"] is False
    assert result["public_observation_execution_performed"] is False
    assert result["paper_transition_blocked"] is True
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_36c_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_public_observation_execution_authorization(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36c_complete"] is False
    assert result["operator_observation_token_ledger_complete"] is False
    assert result["network_off_safety_override_ledger_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_source_36c_has_execution_violation(tmp_path: Path) -> None:
    _write_source_36c(tmp_path, safety_violation=True)
    result = evaluate_public_observation_execution_authorization(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36c_complete"] is False
    assert result["source_36c_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36c_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["public_observation_execution_authorized_now"] is False
    assert result["public_observation_execution_performed"] is False
    assert result["paper_transition_unblocked"] is False
