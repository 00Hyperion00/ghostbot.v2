from __future__ import annotations

import json
from pathlib import Path

from tradebot.post_phase_35_runtime_evidence_strategy import evaluate_post_phase_35_runtime_evidence_strategy


def _write_source_35i(root: Path, *, status: str = "READY", phase_35_closed: bool = True) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "decision": "PHASE_35_FINAL_TAG_AUDIT_READY_NO_SUBMIT_PHASE_35_FINAL_CLOSED",
        "phase_35_closed": phase_35_closed,
        "phase_35_final_closure_ready": phase_35_closed,
        "no_submit_phase_35_final_closed": phase_35_closed,
        "no_submit_phase_35_final_closure_locked": phase_35_closed,
        "phase_35_missing_remote_tag_count": 0,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PHASE_35_FINAL_CLOSURE_NO_SUBMIT",
        "no_submit_phase_35_final_closure_digest": "final-closure-digest",
        "interim_seal_evidence_lock_digest": "interim-lock-digest",
        "phase_35_remote_tag_audit_digest": "remote-tag-audit-digest",
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
        "public_market_data_collection_performed": False,
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
        "phase_35_final_closure_relaxed": False,
    }
    path = reports / "4B436635I_phase_35_final_tag_audit_20260703T112509Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_35i_is_final_closed(tmp_path: Path) -> None:
    _write_source_35i(tmp_path)
    result = evaluate_post_phase_35_runtime_evidence_strategy(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "READY"
    assert result["source_35i_complete"] is True
    assert result["runtime_evidence_collection_policy_complete"] is True
    assert result["runtime_evidence_collection_policy_item_count"] == 6
    assert result["public_data_observation_boundary_complete"] is True
    assert result["public_data_observation_boundary_locked"] is True
    assert result["public_data_observation_boundary_scope_count"] == 5
    assert result["paper_transition_blocker_reduction_plan_complete"] is True
    assert result["paper_transition_blocker_count_carried_forward"] == 4
    assert result["post_phase_35_runtime_evidence_strategy_ready"] is True
    assert result["paper_transition_blocked"] is True
    assert result["approved_for_exchange_submit"] is False
    assert result["order_submit_performed"] is False


def test_not_ready_when_source_35i_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_post_phase_35_runtime_evidence_strategy(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_35i_complete"] is False
    assert result["runtime_evidence_collection_policy_complete"] is False
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_ready"] is False


def test_not_ready_when_source_35i_is_not_final_closed(tmp_path: Path) -> None:
    _write_source_35i(tmp_path, phase_35_closed=False)
    result = evaluate_post_phase_35_runtime_evidence_strategy(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
    )

    assert result["status"] == "NOT_READY"
    assert result["source_35i_complete"] is False
    assert result["post_phase_35_runtime_evidence_strategy_ready"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_unblocked"] is False
