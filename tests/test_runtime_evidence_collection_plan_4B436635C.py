from __future__ import annotations

import json
from pathlib import Path

from tradebot.runtime_evidence_collection_plan import evaluate

SOURCE_DECISION = "RUNTIME_READINESS_EVIDENCE_EXPANSION_READY_NO_SUBMIT_EVIDENCE_PACK_LOCKED"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def source_35b_ready() -> dict:
    false_flags = {
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
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
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "destructive_cleanup_performed": False,
        "deduplication_action_performed": False,
        "approval_performed": False,
        "simulated_approval_performed": False,
        "submit_boundary_relaxed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "runtime_readiness_unlock_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "runtime_evidence_collection_performed": False,
    }
    return {
        "ok": True,
        "status": "READY",
        "decision": SOURCE_DECISION,
        "patch_id": "4B436635B",
        "source_35a_complete": True,
        "phase_34_closed": True,
        "phase_35_planning_only": True,
        "readiness_blocker_detail_ledger_complete": True,
        "readiness_blocker_detail_count": 5,
        "paper_transition_criteria_matrix_complete": True,
        "paper_transition_criteria_open_count": 4,
        "no_submit_runtime_evidence_pack_complete": True,
        "no_submit_runtime_evidence_pack_digest": "packdigest",
        "runtime_evidence_pack_item_count": 4,
        "runtime_readiness_evidence_expanded": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "runtime_readiness_blocker_count": 5,
        **false_flags,
    }


def test_ready_collection_plan(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_json(reports / "4B436635B_runtime_readiness_evidence_expansion_20260703T103515Z_ready.json", source_35b_ready())
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=True)
    assert result["status"] == "READY"
    assert result["source_35b_complete"] is True
    assert result["evidence_source_registry_complete"] is True
    assert result["evidence_source_count"] == 5
    assert result["collection_runbook_matrix_complete"] is True
    assert result["collection_runbook_count"] == 5
    assert result["no_submit_collection_boundary_complete"] is True
    assert result["no_submit_collection_boundary_locked"] is True
    assert result["runtime_evidence_collection_performed"] is False
    assert result["paper_transition_blocked"] is True
    assert Path(result["report_path"]).exists()


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)
    assert result["status"] == "NOT_READY"
    assert result["source_35b_complete"] is False
    assert "SOURCE_35B_READY_REPORT_MISSING" in result["errors"]


def test_source_safety_violation_blocks(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    source = source_35b_ready()
    source["approved_for_exchange_submit"] = True
    write_json(reports / "4B436635B_runtime_readiness_evidence_expansion_20260703T103515Z_ready.json", source)
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)
    assert result["status"] == "NOT_READY"
    assert result["source_35b_complete"] is False
    assert "approved_for_exchange_submit" in result["source_35b_safety_violations"]
