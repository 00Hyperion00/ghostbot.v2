from __future__ import annotations

import json
from pathlib import Path

from tradebot.transition_approval_dry_run import build_report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_ready_34d(repo: Path) -> None:
    write_json(
        repo / "reports" / "recovery" / "4B436634D_operator_decision_token_20260703T094605Z_ready.json",
        {
            "status": "READY",
            "decision": "OPERATOR_DECISION_TOKEN_READY_FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED",
            "source_34c_complete": True,
            "human_review_signature_ledger_complete": True,
            "human_review_signature_required": True,
            "human_review_signature_present": False,
            "human_review_signature_status": "HUMAN_REVIEW_SIGNATURE_NOT_PRESENT_NO_UNLOCK_ONLY",
            "operator_decision_token_present": False,
            "transition_eligibility_dry_run_complete": True,
            "transition_eligibility_status": "TRANSITION_ELIGIBILITY_DRY_RUN_HOLD_OPERATOR_SIGNATURE_REQUIRED",
            "final_no_submit_unlock_boundary_complete": True,
            "final_no_submit_unlock_boundary_status": "FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED",
            "unlock_boundary_locked": True,
            "transition_to_next_phase_allowed": False,
            "transition_to_next_phase_performed": False,
            "next_phase_unlock_allowed": False,
            "next_phase_unlock_performed": False,
            "submit_boundary_relaxed": False,
            "dirty_worktree_blocker_count": 0,
            "dirty_worktree_advisory_only": True,
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
            "file_move_performed": False,
            "report_delete_performed": False,
            "destructive_cleanup_performed": False,
            "deduplication_action_performed": False,
            "manifest_sha256": "m" * 64,
            "immutable_plan_digest": "i" * 64,
            "baseline_digest": "b" * 64,
            "evidence_review_digest": "e" * 64,
            "no_submit_boundary_digest": "n" * 64,
            "transition_decision_digest": "t" * 64,
            "human_review_signature_digest": "h" * 64,
            "transition_eligibility_digest": "y" * 64,
            "final_no_submit_unlock_boundary_digest": "f" * 64,
        },
    )


def test_34e_ready_with_34d_ready(tmp_path: Path) -> None:
    make_ready_34d(tmp_path)

    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.source_34d_complete is True
    assert report.operator_signature_template_complete is True
    assert report.eligibility_matrix_freeze_complete is True
    assert report.eligibility_matrix_frozen is True
    assert report.no_submit_handoff_ledger_complete is True
    assert report.no_submit_handoff_ready is True
    assert report.handoff_performed is False
    assert report.next_phase_unlock_allowed is False
    assert report.transition_to_next_phase_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.order_submit_performed is False


def test_34e_not_ready_without_source_34d(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert report.source_34d_complete is False
    assert report.next_phase_unlock_allowed is False
    assert report.transition_to_next_phase_performed is False
    assert report.file_delete_performed is False
    assert report.exchange_submit_performed is False


def test_34e_writes_all_ledgers(tmp_path: Path) -> None:
    make_ready_34d(tmp_path)
    out_dir = tmp_path / "reports" / "recovery"

    report = build_report(tmp_path, write=True, reports_dir=out_dir)

    assert report.ok is True
    assert report.report_path is not None and Path(report.report_path).exists()
    assert report.operator_signature_template_path is not None and Path(report.operator_signature_template_path).exists()
    assert report.eligibility_matrix_freeze_path is not None and Path(report.eligibility_matrix_freeze_path).exists()
    assert report.no_submit_handoff_ledger_path is not None and Path(report.no_submit_handoff_ledger_path).exists()
