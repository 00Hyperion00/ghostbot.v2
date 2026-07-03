from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path

PATCH_ID = "4B436633H_H1"
PATCH_VERSION = "4B.4.3.6.6.33H-H1"
READY_DECISION = "SOURCE_33G_COMPLETION_GATE_HOTFIX_READY"
NOT_READY_DECISION = "SOURCE_33G_COMPLETION_GATE_HOTFIX_NOT_READY"

REQUIRED_FILES = [
    "src/tradebot/archive_execution_approval_ledger.py",
    "tools/check_4B436633H_H1_source_33g_gate_hotfix.py",
    "tools/run_4B436633H_H1_source_33g_gate_hotfix.py",
    "tests/test_archive_execution_approval_ledger_h1_4B436633H_H1.py",
    "docs/ARCHIVE_EXECUTION_APPROVAL_LEDGER_SOURCE_33G_GATE_HOTFIX_4B436633H_H1.md",
    "README_APPLY_4B436633H_H1.txt",
]


def _bootstrap() -> Path:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return root


def build_summary(root: Path) -> dict[str, object]:
    compile_errors: dict[str, str] = {}
    for rel in REQUIRED_FILES:
        path = root / rel
        if rel.endswith(".py") and path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                compile_errors[rel] = f"{type(exc).__name__}: {exc}"

    from tradebot.archive_execution_approval_ledger import build_archive_execution_approval_ledger_report, summarize_report

    report = build_archive_execution_approval_ledger_report(root)
    source_summary = summarize_report(report)
    ready = (
        not compile_errors
        and source_summary.get("status") == "READY"
        and source_summary.get("decision") == "ARCHIVE_EXECUTION_APPROVAL_LEDGER_READY_FINAL_NO_EXECUTION_GATE_LOCKED"
        and source_summary.get("source_33g_complete") is True
        and source_summary.get("immutable_plan_digest_complete") is True
        and source_summary.get("final_no_execution_gate_complete") is True
        and source_summary.get("archive_execution_allowed") is False
        and source_summary.get("archive_move_performed") is False
        and source_summary.get("file_delete_performed") is False
    )
    return {
        "check_name": "source_33g_completion_gate_hotfix",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "ok": ready,
        "required_files_present": all((root / rel).exists() for rel in REQUIRED_FILES),
        "missing_files": [rel for rel in REQUIRED_FILES if not (root / rel).exists()],
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "source_33g_complete": source_summary.get("source_33g_complete"),
        "source_33g_report": source_summary.get("source_33g_report"),
        "source_33g_decision": source_summary.get("source_33g_decision"),
        "source_33h_status_after_hotfix": source_summary.get("status"),
        "source_33h_decision_after_hotfix": source_summary.get("decision"),
        "source_33h_ready_after_hotfix": source_summary.get("status") == "READY",
        "archive_execution_approval_ledger_complete": source_summary.get("archive_execution_approval_ledger_complete"),
        "immutable_plan_digest_complete": source_summary.get("immutable_plan_digest_complete"),
        "manifest_sha256": source_summary.get("manifest_sha256"),
        "dry_run_archive_move_record_count": source_summary.get("dry_run_archive_move_record_count"),
        "dry_run_archive_total_file_count": source_summary.get("dry_run_archive_total_file_count"),
        "rollback_record_count": source_summary.get("rollback_record_count"),
        "final_no_execution_gate_complete": source_summary.get("final_no_execution_gate_complete"),
        "human_approval_token_present": source_summary.get("human_approval_token_present"),
        "human_approval_token_status": source_summary.get("human_approval_token_status"),
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activated": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633H-H1 source 33G completion gate hotfix.")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    summary = build_summary(_bootstrap())
    print(json.dumps(summary, sort_keys=True) if args.once_json else json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
