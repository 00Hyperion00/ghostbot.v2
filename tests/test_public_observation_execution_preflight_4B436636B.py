from __future__ import annotations

import json
from pathlib import Path

from tradebot.public_observation_execution_preflight import evaluate_public_observation_execution_preflight


def _write_source_36a(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_READY_NO_SUBMIT_POLICY_BOUNDARY_LOCKED",
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "post_phase_35_runtime_evidence_strategy_ready": True,
        "runtime_evidence_collection_policy_complete": True,
        "runtime_evidence_collection_policy_digest": "policy-digest",
        "public_data_observation_boundary_locked": True,
        "public_data_observation_boundary_digest": "boundary-digest",
        "paper_transition_blocker_reduction_plan_complete": True,
        "paper_transition_blocker_reduction_plan_digest": "blocker-plan-digest",
        "no_submit_phase_36a_strategy_boundary_locked": True,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_POST_PHASE_35_STRATEGY_ONLY_NO_SUBMIT",
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
        "public_market_data_collection_performed": safety_violation,
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
        "paper_blocker_reduction_performed": False,
        "runtime_policy_relaxed": False,
    }
    path = reports / "4B436636A_post_phase_35_runtime_evidence_strategy_20260703T113005Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36a_is_strategy_ready(tmp_path: Path) -> None:
    _write_source_36a(tmp_path)
    result = evaluate_public_observation_execution_preflight(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36a_complete"] is True
    assert result["read_only_public_endpoint_contract_complete"] is True
    assert result["read_only_public_endpoint_count"] == 4
    assert result["observation_artifact_schema_complete"] is True
    assert result["observation_artifact_schema_field_count"] == 9
    assert result["no_submit_execution_readiness_gate_complete"] is True
    assert result["public_observation_execution_preflight_ready"] is True
    assert result["public_observation_execution_allowed_now"] is False
    assert result["public_observation_execution_performed"] is False
    assert result["paper_transition_blocked"] is True
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_36a_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_public_observation_execution_preflight(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36a_complete"] is False
    assert result["read_only_public_endpoint_contract_complete"] is False
    assert result["observation_artifact_schema_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_source_36a_has_execution_violation(tmp_path: Path) -> None:
    _write_source_36a(tmp_path, safety_violation=True)
    result = evaluate_public_observation_execution_preflight(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36a_complete"] is False
    assert result["source_36a_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36a_safety_violations"]
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_unblocked"] is False
