from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436638C"
PATCH_VERSION = "4B.4.3.6.6.38C"
PATCH_NAME = "Paper Sandbox Dry-Run Runtime Harness"
ROOT = Path(__file__).resolve().parents[1]
WRITTEN_FILES = [
    "README_APPLY_4B436638C.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_4B436638C.md",
    "src/tradebot/paper_sandbox_dry_run_runtime_harness.py",
    "tests/test_paper_sandbox_dry_run_runtime_harness_4B436638C.py",
    "tools/check_4B436638C_paper_sandbox_dry_run_runtime_harness.py",
    "tools/run_4B436638C_paper_sandbox_dry_run_runtime_harness.py",
    "tools/rollback_4B436638C_paper_sandbox_dry_run_runtime_harness.py",
]


def main() -> int:
    missing = [path for path in WRITTEN_FILES if not (ROOT / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in WRITTEN_FILES:
        if rel.endswith(".py") and (ROOT / rel).exists():
            try:
                py_compile.compile(str(ROOT / rel), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)

    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "paper_sandbox_dry_run_runtime_harness_written": not missing,
        "paper_sandbox_dry_run_runtime_harness_source_mutation_performed": True,
        "paper_sandbox_dry_run_runtime_harness_runtime_binding_performed": False,
        "py_compile_ok": not compile_errors,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "written_files": WRITTEN_FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
