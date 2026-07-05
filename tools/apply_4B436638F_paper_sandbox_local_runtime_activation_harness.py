from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436638F"
PATCH_VERSION = "4B.4.3.6.6.38F"
PATCH_NAME = "Paper Sandbox Local Runtime Activation Harness"

REQUIRED_FILES = [
    "README_APPLY_4B436638F.txt",
    "docs/PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_4B436638F.md",
    "src/tradebot/paper_sandbox_local_runtime_activation_harness.py",
    "tests/test_paper_sandbox_local_runtime_activation_harness_4B436638F.py",
    "tools/check_4B436638F_paper_sandbox_local_runtime_activation_harness.py",
    "tools/run_4B436638F_paper_sandbox_local_runtime_activation_harness.py",
    "tools/rollback_4B436638F_paper_sandbox_local_runtime_activation_harness.py",
]


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not Path(path).exists()]
    compile_errors: dict[str, str] = {}
    for path in [p for p in REQUIRED_FILES if p.endswith(".py") and Path(p).exists()]:
        try:
            py_compile.compile(path, doraise=True)
        except Exception as exc:  # pragma: no cover - defensive
            compile_errors[path] = str(exc)

    result: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": REQUIRED_FILES,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "backed_up_files": [],
        "backup_root": "",
        "modified_files": [],
        "paper_sandbox_local_runtime_activation_harness_written": not missing,
        "paper_sandbox_local_runtime_activation_harness_source_mutation_performed": True,
        "paper_sandbox_local_runtime_activation_harness_runtime_binding_performed": False,
        "local_runtime_activation_harness_runtime_binding_performed": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
