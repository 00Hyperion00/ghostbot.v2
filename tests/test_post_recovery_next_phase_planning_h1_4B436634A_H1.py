
from __future__ import annotations

import json
from pathlib import Path

from tradebot.post_recovery_next_phase_planning import READY_DECISION, build_report, count_value


def _seed_required_files(root: Path) -> None:
    for rel in (
        "src/tradebot/post_recovery_next_phase_planning.py",
        "tools/check_4B436634A_post_recovery_next_phase_planning.py",
        "tools/run_4B436634A_post_recovery_next_phase_planning.py",
        "tests/test_post_recovery_next_phase_planning_4B436634A.py",
        "docs/POST_RECOVERY_NEXT_PHASE_PLANNING_4B436634A.md",
        "README_APPLY_4B436634A.txt",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")


def _write_nested_33i(root: Path, *, unsafe: bool = False) -> None:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "RECOVERY_CLOSURE_REPORT_READY_NEXT_PHASE_LOCKED_NO_RUNTIME_ACTIONS",
        "ok": True,
        "source_33h_gate": {
            "complete": True,
            "manifest_sha256": "0" * 64,
            "immutable_plan_digest": "1" * 64,
        },
        "final_phase_acceptance_matrix": {
            "accepted_for_closure": True,
            "missing_required_phase_tokens": [],
            "rejected_required_phase_tokens": [],
        },
        "git_tag_audit": {
            "missing_tags": [],
            "dirty_worktree_count": 0,
        },
        "next_phase_unlock_plan": {
            "blocking_conditions": [],
            "unlock_allowed": False,
            "unlock_performed": False,
        },
        "safety_snapshot": {
            "approved_for_live_real": False,
            "approved_for_paper_transition": False,
            "approved_for_exchange_submit": False,
            "approved_for_runtime_overlay": False,
            "archive_execution_allowed": False,
            "archive_move_performed": False,
            "file_delete_performed": False,
            "destructive_cleanup_performed": False,
            "exchange_submit_performed": unsafe,
            "trading_action_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "runtime_overlay_activated": False,
            "next_phase_unlock_performed": False,
        },
    }
    (reports / "4B436633I_recovery_closure_report_20260703T091500Z_ready.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_count_value_reads_nested_lists() -> None:
    assert count_value({"a": {"b": [1, 2, 3]}}, "a.b") == 3
    assert count_value({"a": {"b": 2}}, "a.b") == 2


def test_nested_33i_full_report_is_accepted(tmp_path: Path) -> None:
    _seed_required_files(tmp_path)
    _write_nested_33i(tmp_path)
    report, source, *_ = build_report(tmp_path)
    assert source.complete is True
    assert report.source_33i_complete is True
    assert report.status == "READY"
    assert report.ok is True
    assert report.decision == READY_DECISION
    assert report.acceptance_criteria_matrix_complete is True
    assert report.rejected_required_criterion_count == 0
    assert report.exchange_submit_performed is False
    assert report.next_phase_unlock_allowed is False


def test_nested_33i_safety_violation_fails_closed(tmp_path: Path) -> None:
    _seed_required_files(tmp_path)
    _write_nested_33i(tmp_path, unsafe=True)
    report, source, *_ = build_report(tmp_path)
    assert source.complete is False
    assert report.status == "NOT_READY"
    assert report.ok is False
