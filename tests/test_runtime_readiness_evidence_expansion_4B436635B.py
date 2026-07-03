from __future__ import annotations

import json
from pathlib import Path

from tradebot.runtime_readiness_evidence_expansion import evaluate


def write_source(root: Path, overrides: dict[str, object] | None = None) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    source: dict[str, object] = {
        "status": "READY",
        "decision": "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_READY_NO_SUBMIT_BOUNDARY_CARRIED_FORWARD",
        "source_34i_complete": True,
        "phase_34_closed": True,
        "no_submit_runtime_readiness_matrix_complete": True,
        "paper_transition_blocker_ledger_complete": True,
        "safety_boundary_carry_forward_complete": True,
        "accepted_for_runtime_readiness_planning": True,
        "phase_35_planning_only": True,
        "paper_transition_blocked": True,
        "paper_transition_unblocked": False,
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
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "runtime_readiness_unlock_performed": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "runtime_readiness_blocker_count": 5,
        "paper_transition_blocker_count": 4,
        "runtime_readiness_matrix_digest": "runtime-matrix-digest",
        "safety_boundary_carry_forward_digest": "boundary-digest",
        "phase_34_final_seal_digest": "phase-34-seal-digest",
    }
    if overrides:
        source.update(overrides)
    path = reports / "4B436635A_post_governance_runtime_readiness_planning_20260703T000000Z_ready.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    return path


def test_ready_with_valid_35a_source(tmp_path: Path) -> None:
    write_source(tmp_path)
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=True)
    assert result["status"] == "READY"
    assert result["source_35a_complete"] is True
    assert result["readiness_blocker_detail_ledger_complete"] is True
    assert result["paper_transition_criteria_matrix_complete"] is True
    assert result["no_submit_runtime_evidence_pack_complete"] is True
    assert result["paper_transition_blocked"] is True
    assert result["paper_transition_unblocked"] is False
    assert result["next_phase_unlock_allowed"] is False
    assert result["approved_for_exchange_submit"] is False
    assert Path(str(result["report_path"])).exists()


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)
    assert result["status"] == "NOT_READY"
    assert result["source_35a_complete"] is False
    assert "SOURCE_35A_READY_REPORT_MISSING" in result["errors"]


def test_source_safety_violation_blocks_ready(tmp_path: Path) -> None:
    write_source(tmp_path, {"approved_for_paper_transition": True})
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)
    assert result["status"] == "NOT_READY"
    assert result["source_35a_complete"] is False
    assert "approved_for_paper_transition" in result["source_35a_safety_violations"]
