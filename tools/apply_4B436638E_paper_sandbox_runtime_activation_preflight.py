from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436638E"
PATCH_VERSION = "4B.4.3.6.6.38E"
PATCH_NAME = "Paper Sandbox Runtime Activation Preflight"

WRITTEN_FILES = [
    "README_APPLY_4B436638E.txt",
    "docs/PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_4B436638E.md",
    "src/tradebot/paper_sandbox_runtime_activation_preflight.py",
    "tests/test_paper_sandbox_runtime_activation_preflight_4B436638E.py",
    "tools/check_4B436638E_paper_sandbox_runtime_activation_preflight.py",
    "tools/run_4B436638E_paper_sandbox_runtime_activation_preflight.py",
    "tools/rollback_4B436638E_paper_sandbox_runtime_activation_preflight.py",
]

SAFETY_FALSE = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "backed_up_files": [],
    "backup_root": "",
    "deduplication_action_performed": False,
    "destructive_cleanup_performed": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "git_add_performed": False,
    "git_commit_performed": False,
    "git_push_performed": False,
    "git_tag_performed": False,
    "http_request_performed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "network_submit_allowed": False,
    "next_phase_unlock_performed": False,
    "operator_approval_verification_mutation_performed": False,
    "operator_approval_verification_runtime_binding_performed": False,
    "order_submit_performed": False,
    "paper_order_submit_performed": False,
    "paper_runtime_start_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "reload_performed": False,
    "report_archive_performed": False,
    "report_dedup_performed": False,
    "report_delete_performed": False,
    "report_move_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_start_performed": False,
    "signed_request_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def main() -> int:
    root = Path.cwd()
    missing = [p for p in WRITTEN_FILES if not (root / p).exists()]
    compile_errors: dict[str, str] = {}
    for rel in WRITTEN_FILES:
        if rel.endswith(".py") and (root / rel).exists():
            try:
                py_compile.compile(str(root / rel), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)

    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "missing_files": missing,
        "modified_files": [],
        "written_files": WRITTEN_FILES,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "paper_sandbox_runtime_activation_preflight_written": not missing,
        "paper_sandbox_runtime_activation_preflight_source_mutation_performed": True,
        "paper_sandbox_runtime_activation_preflight_runtime_binding_performed": False,
    }
    result.update(SAFETY_FALSE)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
