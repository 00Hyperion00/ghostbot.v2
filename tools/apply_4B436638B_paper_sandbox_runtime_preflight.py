from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436638B"
PATCH_VERSION = "4B.4.3.6.6.38B"
PATCH_NAME = "Paper Sandbox Runtime Preflight"

FILES = [
    "README_APPLY_4B436638B.txt",
    "docs/PAPER_SANDBOX_RUNTIME_PREFLIGHT_4B436638B.md",
    "src/tradebot/paper_sandbox_runtime_preflight.py",
    "tests/test_paper_sandbox_runtime_preflight_4B436638B.py",
    "tools/check_4B436638B_paper_sandbox_runtime_preflight.py",
    "tools/run_4B436638B_paper_sandbox_runtime_preflight.py",
    "tools/rollback_4B436638B_paper_sandbox_runtime_preflight.py",
]

COMPILE_TARGETS = [
    "src/tradebot/paper_sandbox_runtime_preflight.py",
    "tests/test_paper_sandbox_runtime_preflight_4B436638B.py",
    "tools/check_4B436638B_paper_sandbox_runtime_preflight.py",
    "tools/run_4B436638B_paper_sandbox_runtime_preflight.py",
    "tools/rollback_4B436638B_paper_sandbox_runtime_preflight.py",
]


def main() -> int:
    root = Path.cwd()
    missing = [path for path in FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for target in COMPILE_TARGETS:
        path = root / target
        if path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:  # pragma: no cover
                compile_errors[target] = f"{type(exc).__name__}: {exc}"

    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "paper_sandbox_runtime_preflight_written": True,
        "paper_sandbox_runtime_preflight_source_mutation_performed": True,
        "paper_sandbox_runtime_preflight_runtime_binding_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
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
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
