from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tradebot.post_governance_runtime_readiness_planning import evaluate


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def valid_34i_report() -> dict[str, Any]:
    false_fields = {
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
        "approval_performed": False,
        "simulated_approval_performed": False,
        "submit_boundary_relaxed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    return {
        "status": "READY",
        "decision": "POST_CLOSURE_TAG_AUDIT_READY_NO_SUBMIT_PHASE_34_FINAL_SEALED",
        "source_34h_complete": True,
        "phase_34h_tag_present": True,
        "missing_tag_count": 0,
        "missing_tags": [],
        "required_tag_count": 8,
        "present_tag_count": 8,
        "phase_34_closed": True,
        "no_submit_phase_34_final_sealed": True,
        "accepted_for_phase_34_final_seal": True,
        "phase_34_final_seal_digest": "b0522514b26e10ac4b1240ef2a8448400792dd89f37951f86cd823357e3f05bf",
        "phase_34h_tag_commit": "5090491158dc75ae7b364626102bb94f421330a5",
        **false_fields,
    }


def test_35a_ready_from_valid_34i_source(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_json(reports / "4B436634I_post_closure_tag_audit_20260703T102411Z_ready.json", valid_34i_report())

    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=True)

    assert result["status"] == "READY"
    assert result["source_34i_complete"] is True
    assert result["no_submit_runtime_readiness_matrix_complete"] is True
    assert result["paper_transition_blocker_ledger_complete"] is True
    assert result["safety_boundary_carry_forward_complete"] is True
    assert result["paper_transition_blocked"] is True
    assert result["approved_for_paper_transition"] is False
    assert result["next_phase_unlock_allowed"] is False
    assert result["transition_to_next_phase_performed"] is False
    assert result["report_path"] is not None


def test_35a_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_34i_complete"] is False
    assert "SOURCE_34I_READY_REPORT_MISSING" in result["errors"]
    assert result["approved_for_exchange_submit"] is False
    assert result["order_submit_performed"] is False


def test_35a_rejects_source_safety_violation(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    report = valid_34i_report()
    report["exchange_submit_allowed"] = True
    write_json(reports / "4B436634I_post_closure_tag_audit_20260703T102411Z_ready.json", report)

    result = evaluate(tmp_path, Path("reports/recovery"), write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_34i_complete"] is False
    assert result["source_34i_safety_violation_count"] == 1
    assert result["source_34i_safety_violations"] == ["exchange_submit_allowed"]
    assert result["exchange_submit_allowed"] is False
    assert result["next_phase_unlock_performed"] is False
