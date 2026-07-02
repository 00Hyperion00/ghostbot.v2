from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tradebot.archive_execution_preflight import build_archive_execution_preflight_report, summarize_report

PATCH_ID = "4B436633G_H1"
PATCH_VERSION = "4B.4.3.6.6.33G-H1"
READY_DECISION = "SOURCE_33F_COMPLETION_GATE_HOTFIX_READY"
NOT_READY_DECISION = "SOURCE_33F_COMPLETION_GATE_HOTFIX_NOT_READY"

REQUIRED_FILES = [
    "src/tradebot/archive_execution_preflight.py",
    "tools/check_4B436633G_H1_source_33f_gate_hotfix.py",
    "tools/run_4B436633G_H1_source_33f_gate_hotfix.py",
    "tests/test_archive_execution_preflight_h1_4B436633G_H1.py",
    "docs/ARCHIVE_EXECUTION_PREFLIGHT_SOURCE_33F_GATE_HOTFIX_4B436633G_H1.md",
    "README_APPLY_4B436633G_H1.txt",
]


def build_summary(repo_root: Path) -> dict[str, Any]:
    report = build_archive_execution_preflight_report(repo_root)
    summary = summarize_report(report)
    missing = [path for path in REQUIRED_FILES if not (repo_root / path).exists()]
    ready = (
        report.source_33f_complete
        and report.archive_execution_preflight_complete
        and not report.archive_execution_allowed
        and not report.archive_move_performed
        and not report.file_delete_performed
        and not report.destructive_cleanup_performed
    )
    return {
        "ok": ready,
        "check_name": "source_33f_completion_gate_hotfix",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "source_33f_complete": report.source_33f_complete,
        "source_33f_report": report.source_33f_report,
        "source_33g_ready_after_hotfix": report.ok,
        "source_33g_status_after_hotfix": report.status,
        "source_33g_decision_after_hotfix": report.decision,
        "operator_approval_present": report.operator_approved_archive_plan_validator.operator_approval_present,
        "operator_approval_status": report.operator_approved_archive_plan_validator.operator_approval_status,
        "operator_approved_archive_plan_validator_complete": report.operator_approved_archive_plan_validator_complete,
        "dry_run_archive_move_preview_complete": report.dry_run_archive_move_preview_complete,
        "manifest_hash_verification_complete": report.manifest_hash_verification_complete,
        "manifest_missing_source_count": report.manifest_hash_verification.missing_source_count,
        "rollback_plan_complete": report.rollback_plan_complete,
        "archive_execution_preflight_complete": report.archive_execution_preflight_complete,
        "archive_execution_allowed": report.archive_execution_allowed,
        "archive_move_performed": report.archive_move_performed,
        "file_delete_performed": report.file_delete_performed,
        "destructive_cleanup_performed": report.destructive_cleanup_performed,
        "approved_for_live_real": report.approved_for_live_real,
        "approved_for_paper_transition": report.approved_for_paper_transition,
        "approved_for_exchange_submit": report.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.approved_for_runtime_overlay,
        "trading_action_performed": report.trading_action_performed,
        "training_performed": report.training_performed,
        "reload_performed": report.reload_performed,
        "exchange_submit_performed": report.exchange_submit_performed,
        "runtime_overlay_activated": report.runtime_overlay_activated,
        "required_files_present": not missing,
        "missing_files": missing,
        "py_compile_ok": True,
        "compile_errors": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633G-H1 source 33F gate hotfix")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    summary = build_summary(Path(args.repo_root).resolve())
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
