from __future__ import annotations

import json
from pathlib import Path

from tradebot.paper_transition_readiness_review import (
    APPROVAL_PHRASE,
    READY_DECISION,
    SOURCE_DECISION,
    build_report,
    evaluate_paper_approval,
)


def seed_37l_ready_report(reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "4B436637L_production_hardening_final_closure_20260703T000000Z_ready.json"
    payload = {
        "patch_id": "4B436637L",
        "patch_version": "4B.4.3.6.6.37L",
        "patch_name": "Production Hardening Final Closure",
        "status": "READY",
        "decision": SOURCE_DECISION,
        "phase_37_final_closed": True,
        "p0_hardening_complete_final": True,
        "p0_hardening_final_sealed": True,
        "p0_hardening_gap_count_final": 10,
        "p0_hardening_closed_gap_count_final": 10,
        "p0_hardening_open_gap_count_final": 0,
        "no_submit_production_readiness_sealed": True,
        "production_readiness_status": "NO_SUBMIT_PRODUCTION_READINESS_SEALED_P0_COMPLETE",
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_performed": False,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_evaluate_paper_approval_fails_closed() -> None:
    assert evaluate_paper_approval(None)["result"] == "DENY_PAPER_TRANSITION_APPROVAL_REQUIRED"
    assert evaluate_paper_approval("wrong")["result"] == "DENY_PAPER_TRANSITION_APPROVAL_MISMATCH"
    assert evaluate_paper_approval(APPROVAL_PHRASE)["result"] == "APPROVAL_PRESENT_PAPER_TRANSITION_RUNTIME_DENIED_NO_SUBMIT"


def test_38a_ready_report_from_37l_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    seed_37l_ready_report(reports_dir)
    report = build_report(tmp_path, reports_dir, write_reports=False)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_37l_status"] == "SOURCE_37L_READY"


def test_paper_approval_gate_does_not_approve_paper(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    seed_37l_ready_report(reports_dir)
    report = build_report(tmp_path, reports_dir, write_reports=False)
    assert report["explicit_paper_transition_approval_required"] is True
    assert report["paper_transition_approval_gate_complete"] is True
    assert report["paper_transition_approval_missing_denied"] is True
    assert report["paper_transition_approval_invalid_denied"] is True
    assert report["paper_transition_approval_valid_runtime_denied_no_submit"] is True
    assert report["approved_for_paper_transition"] is False
    assert report["paper_runtime_start_performed"] is False


def test_no_live_no_exchange_submit_locked(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    seed_37l_ready_report(reports_dir)
    report = build_report(tmp_path, reports_dir, write_reports=False)
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["exchange_submit_allowed"] is False
    assert report["network_submit_allowed"] is False
    assert report["order_submit_performed"] is False
    assert report["exchange_submit_performed"] is False
    assert report["network_request_performed"] is False
    assert report["signed_request_performed"] is False


def test_writes_reports_without_mutating_runtime(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    seed_37l_ready_report(reports_dir)
    report = build_report(tmp_path, reports_dir, write_reports=True)
    assert report["report_path"] is not None
    assert Path(report["report_path"]).exists()
    assert report["paper_transition_readiness_review_path"] is not None
    assert report["paper_transition_approval_gate_path"] is not None
    assert report["no_live_no_exchange_submit_guard_path"] is not None
    assert report["runtime_start_performed"] is False
    assert report["runtime_overlay_activated"] is False
    assert report["training_performed"] is False
    assert report["reload_performed"] is False


def test_not_ready_without_37l_source(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, reports_dir, write_reports=False)
    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_37l_status"] == "SOURCE_37L_NOT_READY"
