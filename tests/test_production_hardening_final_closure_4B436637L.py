from __future__ import annotations

import json
from pathlib import Path

from tradebot.production_hardening_final_closure import (
    PATCH_VERSION,
    READY_DECISION,
    REQUIRED_PHASE_37_TAGS,
    build_report,
)


def seed_37k_ready(tmp_path: Path) -> Path:
    reports = tmp_path / "reports" / "recovery"
    reports.mkdir(parents=True)
    payload = {
        "patch_id": "4B436637K",
        "patch_version": "4B.4.3.6.6.37K",
        "patch_name": "Promotion Gate Isolation",
        "status": "READY",
        "decision": "PROMOTION_GATE_ISOLATION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_10_LOCKED",
        "source_37j_complete": True,
        "p0_promotion_gate_isolation_closed": True,
        "p0_promotion_gate_isolation_closed_by": "4B.4.3.6.6.37K",
        "p0_hardening_complete": True,
        "p0_hardening_closed_gap_count_after_37k": 10,
        "p0_hardening_open_gap_count_after_37k": 0,
        "all_p0_closed_does_not_enable_paper": True,
        "all_p0_closed_does_not_enable_live": True,
        "all_p0_closed_does_not_enable_submit": True,
        "promotion_gate_isolation_locked": True,
        "cross_phase_promotion_guard_locked": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
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
        "next_phase_unlock_allowed": False,
        "phase_37_planning_only": True,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
    }
    path = reports / "4B436637K_promotion_gate_isolation_20260703T000000Z_ready.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_37l_ready_report_closes_final_seal(tmp_path: Path) -> None:
    seed_37k_ready(tmp_path)
    report = build_report(repo_root=tmp_path)
    assert report["ok"] is True
    assert report["status"] == "READY"
    assert report["decision"] == READY_DECISION
    assert report["source_37k_status"] == "SOURCE_37K_READY"
    assert report["p0_hardening_complete_after_37l"] is True
    assert report["p0_hardening_closed_gap_count_after_37l"] == 10
    assert report["p0_hardening_open_gap_count_after_37l"] == 0
    assert report["no_submit_production_readiness_sealed"] is True


def test_37l_never_unlocks_paper_live_or_submit(tmp_path: Path) -> None:
    seed_37k_ready(tmp_path)
    report = build_report(repo_root=tmp_path)
    assert report["paper_transition_blocked"] is True
    assert report["paper_transition_ready"] is False
    assert report["approved_for_paper_transition"] is False
    assert report["approved_for_live_real"] is False
    assert report["approved_for_exchange_submit"] is False
    assert report["network_submit_allowed"] is False
    assert report["order_submit_performed"] is False
    assert report["exchange_submit_performed"] is False


def test_remote_tag_audit_is_contract_without_network(tmp_path: Path) -> None:
    seed_37k_ready(tmp_path)
    report = build_report(repo_root=tmp_path)
    assert report["remote_tag_audit_complete"] is True
    assert report["remote_tag_audit_locked"] is True
    assert report["remote_tag_audit_operator_review_required"] is True
    assert report["required_phase_37_remote_tag_count"] == len(REQUIRED_PHASE_37_TAGS)
    assert report["git_ls_remote_performed"] is False
    assert report["git_fetch_performed"] is False
    assert report["network_request_performed"] is False
    assert report["git_commit_performed"] is False


def test_final_gate_counts_are_stable(tmp_path: Path) -> None:
    seed_37k_ready(tmp_path)
    report = build_report(repo_root=tmp_path)
    assert report["p0_hardening_final_audit_rule_count"] == 12
    assert report["p0_hardening_final_audit_ready_count"] == 12
    assert report["remote_tag_audit_probe_count"] == 5
    assert report["remote_tag_audit_probe_passed_count"] == 5
    assert report["no_submit_production_readiness_final_gate_check_count"] == 24
    assert report["no_submit_production_readiness_final_gate_ready_count"] == 24


def test_write_reports_creates_component_ledgers(tmp_path: Path) -> None:
    seed_37k_ready(tmp_path)
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(repo_root=tmp_path, reports_dir=reports_dir, write_reports=True)
    assert report["ok"] is True
    assert Path(report["p0_hardening_final_audit_path"]).exists()
    assert Path(report["remote_tag_audit_contract_path"]).exists()
    assert Path(report["no_submit_production_readiness_seal_path"]).exists()
    assert Path(report["no_submit_production_readiness_final_gate_path"]).exists()
    assert Path(report["report_path"]).exists()


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    report = build_report(repo_root=tmp_path)
    assert report["ok"] is False
    assert report["status"] == "NOT_READY"
    assert report["source_37k_status"] == "SOURCE_37K_NOT_READY"
    assert report["decision"] != READY_DECISION
