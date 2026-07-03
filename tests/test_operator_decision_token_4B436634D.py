from __future__ import annotations

import json
from pathlib import Path

from tradebot.operator_decision_token import build_report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_ready_34c(repo: Path) -> None:
    write_json(
        repo / "reports" / "recovery" / "4B436634C_operator_review_gate_20260703T093741Z_ready.json",
        {
            "status": "READY",
            "decision": "OPERATOR_REVIEW_GATE_READY_NO_SUBMIT_RECONFIRMED",
            "source_34b_complete": True,
            "evidence_baseline_review_complete": True,
            "no_submit_boundary_reconfirmation_complete": True,
            "transition_decision_ledger_complete": True,
            "operator_review_required": True,
            "operator_review_present": False,
            "transition_to_next_phase_allowed": False,
            "transition_to_next_phase_performed": False,
            "next_phase_unlock_allowed": False,
            "next_phase_unlock_performed": False,
            "dirty_worktree_advisory_only": True,
            "dirty_worktree_blocker_count": 0,
            "deduplication_action_performed": False,
            "report_delete_performed": False,
            "file_move_performed": False,
            "duplicate_group_count": 27,
            "duplicate_report_count": 31,
            "recovery_report_scanned_count": 70,
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
            "manifest_sha256": "m" * 64,
            "immutable_plan_digest": "i" * 64,
            "baseline_digest": "b" * 64,
            "evidence_review_digest": "e" * 64,
            "no_submit_boundary_digest": "n" * 64,
            "transition_decision_digest": "t" * 64,
        },
    )


def test_34d_ready_with_34c_ready(tmp_path: Path) -> None:
    make_ready_34c(tmp_path)

    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.source_34c_complete is True
    assert report.human_review_signature_ledger_complete is True
    assert report.human_review_signature_present is False
    assert report.operator_decision_token_present is False
    assert report.transition_eligibility_dry_run_complete is True
    assert report.final_no_submit_unlock_boundary_complete is True
    assert report.unlock_boundary_locked is True
    assert report.next_phase_unlock_allowed is False
    assert report.transition_to_next_phase_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.order_submit_performed is False


def test_34d_not_ready_without_source_34c(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert report.source_34c_complete is False
    assert report.next_phase_unlock_allowed is False
    assert report.transition_to_next_phase_performed is False
    assert report.file_delete_performed is False
    assert report.exchange_submit_performed is False


def test_34d_writes_all_ledgers(tmp_path: Path) -> None:
    make_ready_34c(tmp_path)
    out_dir = tmp_path / "reports" / "recovery"

    report = build_report(tmp_path, write=True, reports_dir=out_dir)

    assert report.ok is True
    assert report.report_path is not None and Path(report.report_path).exists()
    assert report.human_review_signature_ledger_path is not None and Path(report.human_review_signature_ledger_path).exists()
    assert report.transition_eligibility_dry_run_path is not None and Path(report.transition_eligibility_dry_run_path).exists()
    assert report.final_no_submit_unlock_boundary_path is not None and Path(report.final_no_submit_unlock_boundary_path).exists()
