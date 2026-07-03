
from __future__ import annotations

import json
import py_compile
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.post_recovery_next_phase_planning import READY_DECISION, build_report

PATCH_ID = "4B436634A_H1"
PATCH_VERSION = "4B.4.3.6.6.34A-H1"
PATCH_NAME = "Source 33I Completion Gate Hotfix"
H1_READY_DECISION = "SOURCE_33I_COMPLETION_GATE_HOTFIX_READY"
H1_NOT_READY_DECISION = "SOURCE_33I_COMPLETION_GATE_HOTFIX_NOT_READY"
REQUIRED_FILES = [
    "src/tradebot/post_recovery_next_phase_planning.py",
    "tools/check_4B436634A_post_recovery_next_phase_planning.py",
    "tools/run_4B436634A_post_recovery_next_phase_planning.py",
    "tests/test_post_recovery_next_phase_planning_4B436634A.py",
    "docs/POST_RECOVERY_NEXT_PHASE_PLANNING_4B436634A.md",
    "README_APPLY_4B436634A.txt",
]


def check() -> dict[str, Any]:
    missing_files = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    compile_errors: dict[str, str] = {}
    target = ROOT / "src" / "tradebot" / "post_recovery_next_phase_planning.py"
    try:
        py_compile.compile(str(target), doraise=True)
    except Exception as exc:
        compile_errors[str(target.relative_to(ROOT))] = str(exc)

    report, *_ = build_report(ROOT)
    h1_ok = (
        not missing_files
        and not compile_errors
        and report.status == "READY"
        and report.ok is True
        and report.decision == READY_DECISION
        and report.source_33i_complete is True
        and report.acceptance_criteria_matrix_complete is True
        and report.no_submit_transition_boundary_complete is True
        and report.submit_boundary_relaxed is False
        and report.next_phase_unlock_allowed is False
        and report.next_phase_unlock_performed is False
        and report.exchange_submit_performed is False
        and report.order_submit_performed is False
        and report.trading_action_performed is False
        and report.training_performed is False
        and report.reload_performed is False
        and report.runtime_overlay_activated is False
        and report.archive_execution_allowed is False
        and report.archive_move_performed is False
        and report.file_delete_performed is False
        and report.destructive_cleanup_performed is False
    )
    return {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "check_name": "source_33i_completion_gate_hotfix",
        "status": "READY" if h1_ok else "NOT_READY",
        "ok": h1_ok,
        "decision": H1_READY_DECISION if h1_ok else H1_NOT_READY_DECISION,
        "required_files_present": not missing_files,
        "missing_files": missing_files,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "source_33i_complete": report.source_33i_complete,
        "source_33i_decision": report.source_33i_decision,
        "source_33i_report": report.source_33i_report,
        "source_34a_ready_after_hotfix": report.ok,
        "source_34a_status_after_hotfix": report.status,
        "source_34a_decision_after_hotfix": report.decision,
        "readiness_scope_definition_complete": report.readiness_scope_definition_complete,
        "no_submit_transition_boundary_complete": report.no_submit_transition_boundary_complete,
        "acceptance_criteria_matrix_complete": report.acceptance_criteria_matrix_complete,
        "rejected_required_criterion_count": report.rejected_required_criterion_count,
        "accepted_criterion_count": report.accepted_criterion_count,
        "required_criterion_count": report.required_criterion_count,
        "current_dirty_worktree_count": report.current_dirty_worktree_count,
        "missing_git_tag_count": report.missing_git_tag_count,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "submit_boundary_relaxed": False,
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
    }


def main() -> int:
    summary = check()
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
