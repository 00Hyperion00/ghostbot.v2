
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradebot.signature_package_closure import READY_DECISION, build_report


def write_source_34g(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "SIGNATURE_APPROVAL_PACKAGE_READY_FINAL_NO_SUBMIT_GOVERNANCE_LOCKED",
        "source_34f_complete": True,
        "operator_signature_example_complete": True,
        "approval_simulation_dry_run_complete": True,
        "final_no_submit_governance_ledger_complete": True,
        "governance_locked": True,
        "no_submit_approval_ready": True,
        "real_operator_signature_present": False,
        "signature_file_present": False,
        "signature_file_valid": False,
        "example_is_not_approval": True,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "submit_boundary_relaxed": False,
        "baseline_digest": "baseline-digest",
        "evidence_review_digest": "evidence-digest",
        "eligibility_matrix_freeze_digest": "eligibility-digest",
        "no_submit_approval_digest": "approval-digest",
        "no_submit_handoff_digest": "handoff-digest",
        "final_no_submit_governance_digest": "governance-digest",
        "approval_simulation_digest": "simulation-digest",
        "operator_signature_example_digest": "example-digest",
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
    (reports / "4B436634G_signature_approval_package_20260703T100834Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_ready_closes_no_submit_chain(tmp_path: Path) -> None:
    write_source_34g(tmp_path)
    report = build_report(tmp_path)
    assert report.ok is True
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_34g_complete is True
    assert report.final_governance_acceptance_complete is True
    assert report.no_submit_chain_closure_complete is True
    assert report.phase_34_tag_audit_complete is True
    assert report.tag_audit_blocker_count == 0
    assert report.next_phase_unlock_allowed is False
    assert report.exchange_submit_allowed is False
    assert report.approval_performed is False


def test_not_ready_without_source(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.ok is False
    assert report.status == "NOT_READY"
    assert report.source_34g_complete is False


def test_run_writes_ledgers(tmp_path: Path) -> None:
    write_source_34g(tmp_path)
    report = build_report(tmp_path, write_files=True)
    assert report.ok is True
    assert report.report_path is not None
    assert (tmp_path / report.report_path).exists()
    assert report.final_governance_acceptance_path is not None
    assert (tmp_path / report.final_governance_acceptance_path).exists()
    assert report.no_submit_chain_closure_path is not None
    assert (tmp_path / report.no_submit_chain_closure_path).exists()
    assert report.phase_34_tag_audit_path is not None
    assert (tmp_path / report.phase_34_tag_audit_path).exists()
