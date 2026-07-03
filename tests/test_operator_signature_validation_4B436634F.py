from __future__ import annotations

import json
from pathlib import Path

from tradebot.operator_signature_validation import build_report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_ready_34e(repo: Path) -> dict:
    payload = {
        "status": "READY",
        "decision": "TRANSITION_APPROVAL_DRY_RUN_READY_NO_SUBMIT_HANDOFF_LOCKED",
        "source_34d_complete": True,
        "operator_signature_template_complete": True,
        "operator_signature_template_status": "OPERATOR_SIGNATURE_TEMPLATE_READY_NO_SIGNATURE_PRESENT",
        "human_review_signature_required": True,
        "human_review_signature_present": False,
        "operator_decision_token_present": False,
        "eligibility_matrix_freeze_complete": True,
        "eligibility_matrix_freeze_status": "ELIGIBILITY_MATRIX_FROZEN_NO_UNLOCK",
        "eligibility_matrix_frozen": True,
        "no_submit_handoff_ledger_complete": True,
        "no_submit_handoff_status": "NO_SUBMIT_HANDOFF_LEDGER_READY_BOUNDARY_LOCKED",
        "no_submit_handoff_ready": True,
        "final_no_submit_unlock_boundary_complete": True,
        "final_no_submit_unlock_boundary_status": "FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED",
        "transition_eligibility_dry_run_complete": True,
        "transition_eligibility_status": "TRANSITION_ELIGIBILITY_DRY_RUN_HOLD_OPERATOR_SIGNATURE_REQUIRED",
        "unlock_boundary_locked": True,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "submit_boundary_relaxed": False,
        "handoff_performed": False,
        "manifest_sha256": "manifest",
        "immutable_plan_digest": "immutable",
        "baseline_digest": "baseline",
        "evidence_review_digest": "evidence",
        "no_submit_boundary_digest": "boundary",
        "transition_decision_digest": "transition",
        "human_review_signature_digest": "human",
        "transition_eligibility_digest": "eligibility",
        "final_no_submit_unlock_boundary_digest": "final",
        "operator_signature_template_digest": "template-digest",
        "eligibility_matrix_freeze_digest": "freeze-digest",
        "no_submit_handoff_digest": "handoff-digest",
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
    }
    write_json(repo / "reports" / "recovery" / "4B436634E_transition_approval_dry_run_20260703T095047Z_ready.json", payload)
    return payload


def test_34f_ready_without_signature_file(tmp_path: Path) -> None:
    make_ready_34e(tmp_path)
    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.source_34e_complete is True
    assert report.signature_file_schema_ledger_complete is True
    assert report.signature_file_present is False
    assert report.eligibility_matrix_digest_match_complete is True
    assert report.no_submit_approval_ledger_complete is True
    assert report.next_phase_unlock_allowed is False
    assert report.transition_to_next_phase_allowed is False
    assert report.order_submit_performed is False


def test_34f_not_ready_without_source_34e(tmp_path: Path) -> None:
    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert report.source_34e_complete is False
    assert report.file_delete_performed is False
    assert report.exchange_submit_performed is False
    assert report.next_phase_unlock_performed is False


def test_34f_writes_all_ledgers(tmp_path: Path) -> None:
    make_ready_34e(tmp_path)
    out_dir = tmp_path / "reports" / "recovery"

    report = build_report(tmp_path, write=True, reports_dir=out_dir)

    assert report.ok is True
    assert report.report_path is not None and Path(report.report_path).exists()
    assert report.signature_file_schema_ledger_path is not None and Path(report.signature_file_schema_ledger_path).exists()
    assert report.eligibility_matrix_digest_match_path is not None and Path(report.eligibility_matrix_digest_match_path).exists()
    assert report.no_submit_approval_ledger_path is not None and Path(report.no_submit_approval_ledger_path).exists()
