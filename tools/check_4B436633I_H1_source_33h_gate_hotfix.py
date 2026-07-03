from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.recovery_closure_report import build_recovery_closure_report, summarize_report

PATCH_ID = "4B436633I_H1"
PATCH_VERSION = "4B.4.3.6.6.33I-H1"
READY_DECISION = "SOURCE_33H_CLOSURE_GATE_HOTFIX_READY"

REQUIRED_FILES = [
    "README_APPLY_4B436633I_H1.txt",
    "docs/RECOVERY_CLOSURE_REPORT_SOURCE_33H_GATE_HOTFIX_4B436633I_H1.md",
    "tests/test_recovery_closure_report_h1_4B436633I_H1.py",
    "tools/check_4B436633I_H1_source_33h_gate_hotfix.py",
    "tools/run_4B436633I_H1_source_33h_gate_hotfix.py",
]


def _compile(paths: list[Path]) -> tuple[bool, dict[str, str]]:
    errors: dict[str, str] = {}
    for path in paths:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors[str(path)] = str(exc)
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33I-H1 source 33H gate hotfix check")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    compile_ok, compile_errors = _compile([
        ROOT / "src" / "tradebot" / "recovery_closure_report.py",
        ROOT / "tools" / "check_4B436633I_H1_source_33h_gate_hotfix.py",
        ROOT / "tools" / "run_4B436633I_H1_source_33h_gate_hotfix.py",
    ])
    report = build_recovery_closure_report(ROOT)
    summary = summarize_report(report)
    ok = bool(
        not missing
        and compile_ok
        and summary.get("source_33h_complete") is True
        and summary.get("accepted_for_closure") is True
        and summary.get("decision") == "RECOVERY_CLOSURE_REPORT_READY_NEXT_PHASE_LOCKED_NO_RUNTIME_ACTIONS"
        and summary.get("next_phase_unlock_allowed") is False
        and summary.get("archive_execution_allowed") is False
        and summary.get("exchange_submit_performed") is False
    )
    payload = {
        "check_name": "source_33h_closure_gate_hotfix",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ok": ok,
        "status": "READY" if ok else "NOT_READY",
        "decision": READY_DECISION if ok else "SOURCE_33H_CLOSURE_GATE_HOTFIX_NOT_READY",
        "required_files_present": not missing,
        "missing_files": missing,
        "py_compile_ok": compile_ok,
        "compile_errors": compile_errors,
        "source_33h_complete": summary.get("source_33h_complete"),
        "source_33h_report": summary.get("source_33h_report"),
        "source_33h_decision": summary.get("source_33h_decision"),
        "source_33i_ready_after_hotfix": summary.get("status") == "READY",
        "source_33i_status_after_hotfix": summary.get("status"),
        "source_33i_decision_after_hotfix": summary.get("decision"),
        "manifest_sha256": summary.get("manifest_sha256"),
        "immutable_plan_digest": summary.get("immutable_plan_digest"),
        "accepted_for_closure": summary.get("accepted_for_closure"),
        "dirty_worktree_count": summary.get("dirty_worktree_count"),
        "missing_git_tag_count": summary.get("missing_git_tag_count"),
        "blocking_condition_count": summary.get("blocking_condition_count"),
        "next_phase_unlock_allowed": summary.get("next_phase_unlock_allowed"),
        "next_phase_unlock_performed": summary.get("next_phase_unlock_performed"),
        "archive_execution_allowed": summary.get("archive_execution_allowed"),
        "archive_move_performed": summary.get("archive_move_performed"),
        "file_delete_performed": summary.get("file_delete_performed"),
        "destructive_cleanup_performed": summary.get("destructive_cleanup_performed"),
        "exchange_submit_performed": summary.get("exchange_submit_performed"),
        "trading_action_performed": summary.get("trading_action_performed"),
        "training_performed": summary.get("training_performed"),
        "reload_performed": summary.get("reload_performed"),
        "runtime_overlay_activated": summary.get("runtime_overlay_activated"),
    }
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
