from __future__ import annotations

import json
from pathlib import Path

import tradebot.public_observation_final_closure as mod
from tradebot.public_observation_final_closure import GitState, evaluate_public_observation_final_closure


REQUIRED_REMOTE_TAGS = (
    "4B.4.3.6.6.36A",
    "4B.4.3.6.6.36B",
    "4B.4.3.6.6.36C",
    "4B.4.3.6.6.36D",
    "4B.4.3.6.6.36E",
    "4B.4.3.6.6.36F",
)


def _git_state(remote_tags: tuple[str, ...] = REQUIRED_REMOTE_TAGS) -> GitState:
    return GitState(
        git_available=True,
        git_branch="main",
        git_head_short="abc1234",
        local_phase_36_tags=remote_tags,
        remote_phase_36_tags=remote_tags,
        remote_tag_query_ok=True,
        remote_tag_query_error=None,
    )


def _write_source_36f(root: Path, *, ready: bool = True, safety_violation: bool = False) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY" if ready else "NOT_READY",
        "decision": "PUBLIC_OBSERVATION_EVIDENCE_CLOSURE_READY_NO_SUBMIT_PHASE_36_INTERIM_CLOSED",
        "source_36e_complete": True,
        "phase_35_closed": True,
        "phase_36_planning_only": True,
        "phase_36_interim_closed": True,
        "phase_36_final_closed": False,
        "phase_36_tag_audit_complete": True,
        "phase_36_missing_tag_count": 0,
        "network_off_evidence_digest_lock_complete": True,
        "network_off_evidence_digest_missing_count": 0,
        "no_submit_phase_36_interim_closure_complete": True,
        "public_observation_evidence_closure_ready": True,
        "phase_36_tag_audit_digest": "tag-audit-digest",
        "network_off_evidence_digest_lock_digest": "network-off-evidence-digest-lock",
        "no_submit_phase_36_interim_closure_digest": "interim-closure-digest",
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
        "public_observation_dry_run_collector_executed": False,
        "public_observation_network_off_execution_package_executed": False,
        "public_data_fetch_adapter_executed": False,
        "network_request_allowed_now": False,
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
        "operator_observation_token_consumed": False,
        "operator_observation_token_validated": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_present": False,
        "phase_36_interim_closure_relaxed": False,
        "network_off_evidence_digest_lock_relaxed": False,
        "phase_36_tag_audit_relaxed": False,
        "simulated_approval_performed": False,
    }
    path = reports / "4B436636F_public_observation_evidence_closure_20260703T121049Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_36f_and_remote_tags_are_ready(tmp_path: Path, monkeypatch) -> None:
    _write_source_36f(tmp_path)
    monkeypatch.setattr(mod, "read_git_state", lambda repo_root: _git_state())

    result = evaluate_public_observation_final_closure(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_36f_complete"] is True
    assert result["phase_36_remote_tag_audit_complete"] is True
    assert result["phase_36_required_remote_tag_count"] == 6
    assert result["phase_36_present_remote_tag_count"] == 6
    assert result["phase_36_missing_remote_tag_count"] == 0
    assert result["no_submit_phase_36_final_seal_complete"] is True
    assert result["no_submit_phase_36_final_seal_locked"] is True
    assert result["phase_36_final_closed"] is True
    assert result["no_submit_phase_36_final_closed"] is True
    assert result["public_observation_final_closure_ready"] is True
    assert result["next_phase_unlock_allowed"] is False
    assert result["network_request_performed"] is False
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_36f_report_is_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "read_git_state", lambda repo_root: _git_state())
    result = evaluate_public_observation_final_closure(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36f_complete"] is False
    assert result["phase_36_final_closed"] is False
    assert result["phase_36_remote_tag_audit_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False


def test_not_ready_when_remote_36f_tag_is_missing(tmp_path: Path, monkeypatch) -> None:
    _write_source_36f(tmp_path)
    monkeypatch.setattr(mod, "read_git_state", lambda repo_root: _git_state(REQUIRED_REMOTE_TAGS[:-1]))

    result = evaluate_public_observation_final_closure(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36f_complete"] is True
    assert result["phase_36_remote_tag_audit_complete"] is False
    assert result["phase_36_missing_remote_tag_count"] == 1
    assert "4B.4.3.6.6.36F" in result["phase_36_missing_remote_tags"]
    assert result["phase_36_final_closed"] is False
    assert result["no_submit_phase_36_final_closed"] is False
    assert result["exchange_submit_allowed"] is False


def test_not_ready_when_source_36f_has_execution_violation(tmp_path: Path, monkeypatch) -> None:
    _write_source_36f(tmp_path, safety_violation=True)
    monkeypatch.setattr(mod, "read_git_state", lambda repo_root: _git_state())

    result = evaluate_public_observation_final_closure(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_36f_complete"] is False
    assert result["source_36f_safety_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_36f_safety_violations"]
    assert result["network_request_performed"] is False
    assert result["public_market_data_collection_performed"] is False
    assert result["paper_transition_unblocked"] is False
