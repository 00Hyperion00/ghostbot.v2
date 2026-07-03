from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tradebot.post_recovery_next_phase_planning import READY_DECISION, build_report, run


def write_source_33i(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "RECOVERY_CLOSURE_REPORT_READY_NEXT_PHASE_LOCKED_NO_RUNTIME_ACTIONS",
        "accepted_for_closure": True,
        "source_33h_complete": True,
        "missing_required_phase_count": 0,
        "rejected_required_phase_count": 0,
        "blocking_condition_count": 0,
        "missing_git_tag_count": 0,
        "dirty_worktree_count": 0,
        "manifest_sha256": "m" * 64,
        "immutable_plan_digest": "d" * 64,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "next_phase_unlock_performed": False,
    }
    (reports / "4B436633I_recovery_closure_report_20260703T090000Z_ready.json").write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_ready_with_source_33i(tmp_path: Path) -> None:
    write_source_33i(tmp_path)
    report, *_ = build_report(tmp_path)
    assert report.ok is True
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_33i_complete is True
    assert report.no_submit_transition_boundary_complete is True
    assert report.next_phase_unlock_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.trading_action_performed is False


def test_build_report_not_ready_without_source_33i(tmp_path: Path) -> None:
    report, *_ = build_report(tmp_path)
    assert report.ok is False
    assert report.status == "NOT_READY"
    assert report.source_33i_complete is False
    assert report.rejected_required_criterion_count >= 1


def test_run_writes_evidence_ledgers(tmp_path: Path) -> None:
    write_source_33i(tmp_path)
    report = run(tmp_path, tmp_path / "reports" / "recovery")
    assert report.ok is True
    assert report.report_path is not None
    assert Path(report.report_path).exists()
    assert report.readiness_scope_definition_path is not None
    assert Path(report.readiness_scope_definition_path).exists()
    assert report.no_submit_transition_boundary_path is not None
    assert Path(report.no_submit_transition_boundary_path).exists()
    assert report.acceptance_criteria_matrix_path is not None
    assert Path(report.acceptance_criteria_matrix_path).exists()
