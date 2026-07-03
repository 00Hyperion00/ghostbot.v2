from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tradebot.evidence_inventory_reconciliation import build_report, build_recovery_report_deduplication


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_ready_34a(repo: Path) -> None:
    write_json(
        repo / "reports" / "recovery" / "4B436634A_post_recovery_next_phase_planning_20260703T091913Z_ready.json",
        {
            "status": "READY",
            "decision": "POST_RECOVERY_NEXT_PHASE_PLANNING_READY_NO_SUBMIT_BOUNDARY_LOCKED",
            "source_33i_complete": True,
            "accepted_for_closure": True,
            "readiness_scope_definition_complete": True,
            "no_submit_transition_boundary_complete": True,
            "acceptance_criteria_matrix_complete": True,
            "rejected_required_criterion_count": 0,
            "submit_boundary_relaxed": False,
            "approved_for_live_real": False,
            "approved_for_paper_transition": False,
            "approved_for_exchange_submit": False,
            "approved_for_runtime_overlay": False,
            "live_real_submit_allowed": False,
            "paper_submit_allowed": False,
            "exchange_submit_allowed": False,
            "network_submit_allowed": False,
            "runtime_overlay_allowed": False,
            "exchange_submit_performed": False,
            "order_submit_performed": False,
            "trading_action_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "runtime_overlay_activated": False,
            "archive_execution_allowed": False,
            "archive_move_performed": False,
            "file_delete_performed": False,
            "destructive_cleanup_performed": False,
            "next_phase_unlock_allowed": False,
            "next_phase_unlock_performed": False,
            "manifest_sha256": "m" * 64,
            "immutable_plan_digest": "i" * 64,
        },
    )


def test_34b_ready_with_ready_34a_and_duplicate_reports(tmp_path: Path) -> None:
    make_ready_34a(tmp_path)
    write_json(tmp_path / "reports" / "recovery" / "4B436633I_recovery_closure_report_20260703T010101Z_ready.json", {"status": "READY"})
    write_json(tmp_path / "reports" / "recovery" / "4B436633I_recovery_closure_report_20260703T020202Z_ready.json", {"status": "READY"})

    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.source_34a_complete is True
    assert report.recovery_report_deduplication_complete is True
    assert report.duplicate_group_count >= 1
    assert report.deduplication_action_performed is False
    assert report.next_phase_unlock_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.order_submit_performed is False


def test_34b_not_ready_without_source_34a(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert report.source_34a_complete is False
    assert report.post_34a_evidence_baseline_complete is False
    assert report.archive_execution_allowed is False
    assert report.file_delete_performed is False


def test_34b_writes_all_ledgers(tmp_path: Path) -> None:
    make_ready_34a(tmp_path)
    out_dir = tmp_path / "reports" / "recovery"

    report = build_report(tmp_path, write=True, reports_dir=out_dir)

    assert report.ok is True
    assert report.report_path is not None and Path(report.report_path).exists()
    assert report.recovery_report_deduplication_path is not None and Path(report.recovery_report_deduplication_path).exists()
    assert report.advisory_dirty_worktree_normalizer_path is not None and Path(report.advisory_dirty_worktree_normalizer_path).exists()
    assert report.post_34a_evidence_baseline_path is not None and Path(report.post_34a_evidence_baseline_path).exists()
