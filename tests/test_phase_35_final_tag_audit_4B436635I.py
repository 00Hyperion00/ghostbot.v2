from __future__ import annotations

import json
from pathlib import Path

from tradebot.phase_35_final_tag_audit import REQUIRED_REMOTE_TAGS, evaluate_phase_35_final_tag_audit


def _write_source_35h(root: Path, *, status: str = "READY") -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "decision": "RUNTIME_READINESS_PLANNING_CLOSURE_READY_NO_SUBMIT_PHASE_35_INTERIM_SEALED",
        "no_submit_phase_35_interim_sealed": True,
        "no_submit_phase_35_interim_seal_locked": True,
        "phase_35_planning_closure_ready": True,
        "phase_35_present_tag_count": 7,
        "phase_35_missing_tag_count": 0,
        "no_submit_phase_35_interim_seal_digest": "seal-digest",
        "phase_35_tag_audit_digest": "tag-audit-digest",
        "planning_evidence_acceptance_digest": "acceptance-digest",
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
        "phase_35_interim_seal_relaxed": False,
    }
    path = reports / "4B436635H_runtime_readiness_planning_closure_20260703T111123Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ready_when_source_35h_and_remote_tags_are_complete(tmp_path: Path) -> None:
    _write_source_35h(tmp_path)
    result = evaluate_phase_35_final_tag_audit(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
        remote_tag_names=REQUIRED_REMOTE_TAGS,
    )

    assert result["status"] == "READY"
    assert result["source_35h_complete"] is True
    assert result["phase_35_remote_tag_audit_complete"] is True
    assert result["phase_35_present_remote_tag_count"] == 8
    assert result["phase_35_missing_remote_tag_count"] == 0
    assert result["interim_seal_evidence_lock_complete"] is True
    assert result["no_submit_phase_35_final_closed"] is True
    assert result["paper_transition_blocked"] is True
    assert result["approved_for_exchange_submit"] is False
    assert result["order_submit_performed"] is False


def test_not_ready_when_remote_35h_tag_is_missing(tmp_path: Path) -> None:
    _write_source_35h(tmp_path)
    result = evaluate_phase_35_final_tag_audit(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
        remote_tag_names=REQUIRED_REMOTE_TAGS[:-1],
    )

    assert result["status"] == "NOT_READY"
    assert result["phase_35_remote_tag_audit_complete"] is False
    assert result["phase_35_missing_remote_tags"] == ["4B.4.3.6.6.35H"]
    assert result["transition_to_next_phase_allowed"] is False
    assert result["exchange_submit_allowed"] is False


def test_not_ready_when_source_35h_report_is_missing(tmp_path: Path) -> None:
    result = evaluate_phase_35_final_tag_audit(
        repo_root=tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
        remote_tag_names=REQUIRED_REMOTE_TAGS,
    )

    assert result["status"] == "NOT_READY"
    assert result["source_35h_complete"] is False
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_ready"] is False
