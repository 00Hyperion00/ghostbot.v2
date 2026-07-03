from __future__ import annotations

import json
from pathlib import Path

from tradebot.promotion_gate_isolation import (
    READY_DECISION,
    build_report,
    evaluate_promotion_transition,
)


def seed_source_37j(repo: Path) -> None:
    reports = repo / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "REPORT_COMMIT_POLICY_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_9_LOCKED",
        "p0_report_commit_policy_closed": True,
        "p0_report_commit_policy_closed_by": "4B.4.3.6.6.37J",
        "p0_hardening_closed_gap_count_after_37j": 9,
        "p0_hardening_open_gap_count_after_37j": 1,
        "phase_37_planning_only": True,
        "no_submit_p0_9_hardening_gate_locked": True,
        "report_provenance_guard_locked": True,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "paper_transition_unblocked": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "trading_action_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "git_commit_performed": False,
        "git_add_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "promotion_gate_mutation_performed": False,
        "promotion_state_mutation_performed": False,
        "cross_phase_auto_promotion_performed": False,
        "shadow_to_paper_promotion_performed": False,
        "paper_to_live_promotion_performed": False,
        "live_real_promotion_performed": False,
        "paper_transition_approval_performed": False,
        "live_transition_approval_performed": False,
        "simulated_approval_performed": False,
    }
    (reports / "4B436637J_report_commit_policy_20260703T143303Z_ready.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def test_ready_report_closes_p0_10(tmp_path: Path) -> None:
    seed_source_37j(tmp_path)
    report = build_report(tmp_path)
    assert report["ok"] is True
    assert report["decision"] == READY_DECISION
    assert report["source_37j_status"] == "SOURCE_37J_READY"
    assert report["p0_promotion_gate_isolation_closed"] is True
    assert report["p0_hardening_closed_gap_count_after_37k"] == 10
    assert report["p0_hardening_open_gap_count_after_37k"] == 0
    assert report["p0_hardening_complete"] is True


def test_auto_promotion_denied_without_approval() -> None:
    outcome = evaluate_promotion_transition(
        "shadow_observation",
        "paper_candidate",
        explicit_approval_present=False,
    )
    assert outcome["result"] == "DENY_SHADOW_TO_PAPER_AUTO_PROMOTION"
    assert outcome["promotion_allowed"] is False


def test_valid_approval_still_denied_no_submit() -> None:
    outcome = evaluate_promotion_transition(
        "paper_candidate",
        "live_real_candidate",
        explicit_approval_present=True,
    )
    assert outcome["result"] == "APPROVAL_PRESENT_PROMOTION_DENIED_NO_SUBMIT_HARDENING"
    assert outcome["runtime_execution_allowed"] is False


def test_unknown_gate_denied() -> None:
    outcome = evaluate_promotion_transition(
        "shadow_observation",
        "unknown_gate",
        explicit_approval_present=True,
    )
    assert outcome["result"] == "DENY_UNKNOWN_PROMOTION_GATE"
    assert outcome["promotion_allowed"] is False


def test_no_submit_safety_flags_remain_false(tmp_path: Path) -> None:
    seed_source_37j(tmp_path)
    report = build_report(tmp_path)
    for field in (
        "paper_transition_ready",
        "approved_for_live_real",
        "approved_for_paper_transition",
        "approved_for_exchange_submit",
        "network_submit_allowed",
        "order_submit_performed",
        "exchange_submit_performed",
        "runtime_overlay_activated",
        "transition_to_next_phase_performed",
    ):
        assert report[field] is False
    assert report["paper_transition_blocked"] is True
    assert report["next_phase"] == "4B.4.3.6.6.37L"
    assert report["next_phase_unlock_allowed"] is False


def test_write_reports(tmp_path: Path) -> None:
    seed_source_37j(tmp_path)
    reports_dir = tmp_path / "reports" / "recovery"
    report = build_report(tmp_path, reports_dir, write_reports=True)
    assert report["ok"] is True
    assert Path(report["report_path"]).exists()
    assert Path(report["promotion_gate_isolation_policy_path"]).exists()
    assert Path(report["cross_phase_promotion_guard_path"]).exists()
    assert Path(report["promotion_gate_isolation_probe_path"]).exists()
    assert Path(report["no_submit_p0_10_hardening_gate_path"]).exists()
