from __future__ import annotations

import json
from pathlib import Path

from tradebot.operator_review_gate import build_report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_ready_34b(repo: Path) -> None:
    write_json(
        repo / "reports" / "recovery" / "4B436634B_evidence_inventory_reconciliation_20260703T092707Z_ready.json",
        {
            "status": "READY",
            "decision": "EVIDENCE_INVENTORY_RECONCILIATION_READY_POST_34A_BASELINE_LOCKED",
            "source_34a_complete": True,
            "recovery_report_deduplication_complete": True,
            "advisory_dirty_worktree_normalizer_complete": True,
            "post_34a_evidence_baseline_complete": True,
            "dirty_worktree_advisory_only": True,
            "dirty_worktree_blocker_count": 0,
            "deduplication_action_performed": False,
            "duplicate_group_count": 27,
            "duplicate_report_count": 31,
            "recovery_report_scanned_count": 70,
            "ready_report_count": 25,
            "unknown_report_count": 45,
            "current_dirty_worktree_count": 8,
            "normalized_dirty_worktree_count": 8,
            "submit_boundary_relaxed": False,
            "next_phase_unlock_allowed": False,
            "next_phase_unlock_performed": False,
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
            "manifest_sha256": "m" * 64,
            "immutable_plan_digest": "i" * 64,
            "baseline_digest": "b" * 64,
            "deduplication_digest": "d" * 64,
            "dirty_worktree_digest": "w" * 64,
        },
    )


def test_34c_ready_with_34b_ready(tmp_path: Path) -> None:
    make_ready_34b(tmp_path)

    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.source_34b_complete is True
    assert report.evidence_baseline_review_complete is True
    assert report.no_submit_boundary_reconfirmation_complete is True
    assert report.transition_decision_ledger_complete is True
    assert report.operator_review_required is True
    assert report.operator_review_present is False
    assert report.transition_to_next_phase_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.order_submit_performed is False
    assert report.deduplication_action_performed is False


def test_34c_not_ready_without_source_34b(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert report.source_34b_complete is False
    assert report.no_submit_boundary_reconfirmation_complete is False
    assert report.next_phase_unlock_allowed is False
    assert report.file_delete_performed is False
    assert report.exchange_submit_performed is False


def test_34c_writes_all_ledgers(tmp_path: Path) -> None:
    make_ready_34b(tmp_path)
    out_dir = tmp_path / "reports" / "recovery"

    report = build_report(tmp_path, write=True, reports_dir=out_dir)

    assert report.ok is True
    assert report.report_path is not None and Path(report.report_path).exists()
    assert report.evidence_baseline_review_path is not None and Path(report.evidence_baseline_review_path).exists()
    assert report.no_submit_boundary_reconfirmation_path is not None and Path(report.no_submit_boundary_reconfirmation_path).exists()
    assert report.transition_decision_ledger_path is not None and Path(report.transition_decision_ledger_path).exists()
