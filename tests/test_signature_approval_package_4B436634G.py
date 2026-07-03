
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradebot.signature_approval_package import READY_DECISION, build_report


def write_source_34f(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "OPERATOR_SIGNATURE_VALIDATION_READY_NO_SUBMIT_APPROVAL_LOCKED",
        "source_34e_complete": True,
        "signature_file_schema_ledger_complete": True,
        "signature_file_required": True,
        "signature_file_present": False,
        "signature_file_valid": False,
        "eligibility_matrix_digest_match_complete": True,
        "eligibility_matrix_digest_match": False,
        "no_submit_approval_ledger_complete": True,
        "no_submit_approval_ready": True,
        "unlock_boundary_locked": True,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "submit_boundary_relaxed": False,
        "approval_performed": False,
        "expected_eligibility_matrix_digest": "eligibility-digest",
        "eligibility_matrix_freeze_digest": "eligibility-digest",
        "no_submit_handoff_digest": "handoff-digest",
        "no_submit_approval_digest": "approval-digest",
        "signature_file_schema_digest": "schema-digest",
        "manifest_sha256": "manifest",
        "immutable_plan_digest": "plan",
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
    }
    (reports / "4B436634F_operator_signature_validation_20260703T100151Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_ready_without_real_signature(tmp_path: Path) -> None:
    write_source_34f(tmp_path)
    report = build_report(tmp_path)
    assert report.ok is True
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_34f_complete is True
    assert report.operator_signature_example_complete is True
    assert report.approval_simulation_dry_run_complete is True
    assert report.final_no_submit_governance_ledger_complete is True
    assert report.real_operator_signature_present is False
    assert report.simulated_approval_performed is False
    assert report.next_phase_unlock_allowed is False
    assert report.exchange_submit_allowed is False


def test_not_ready_without_source(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.ok is False
    assert report.status == "NOT_READY"
    assert report.source_34f_complete is False


def test_run_writes_ledgers(tmp_path: Path) -> None:
    write_source_34f(tmp_path)
    report = build_report(tmp_path, write_files=True)
    assert report.ok is True
    assert report.report_path is not None
    assert (tmp_path / report.report_path).exists()
    assert report.operator_signature_example_path is not None
    assert (tmp_path / report.operator_signature_example_path).exists()
    assert report.approval_simulation_dry_run_path is not None
    assert (tmp_path / report.approval_simulation_dry_run_path).exists()
    assert report.final_no_submit_governance_ledger_path is not None
    assert (tmp_path / report.final_no_submit_governance_ledger_path).exists()
