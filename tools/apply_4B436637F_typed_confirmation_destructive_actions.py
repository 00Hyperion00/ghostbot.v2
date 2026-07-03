from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436637F"
PATCH_VERSION = "4B.4.3.6.6.37F"
PATCH_NAME = "Typed Confirmation Destructive Actions"
EXPECTED_FILES = [
    "README_APPLY_4B436637F.txt",
    "docs/TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_4B436637F.md",
    "src/tradebot/typed_confirmation_destructive_actions.py",
    "tests/test_typed_confirmation_destructive_actions_4B436637F.py",
    "tools/check_4B436637F_typed_confirmation_destructive_actions.py",
    "tools/run_4B436637F_typed_confirmation_destructive_actions.py",
    "tools/rollback_4B436637F_typed_confirmation_destructive_actions.py",
]

SAFETY_FALSE = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "deduplication_action_performed": False,
    "destructive_action_execution_performed": False,
    "destructive_endpoint_execution_performed": False,
    "destructive_cleanup_performed": False,
    "evidence_collection_started": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "http_request_performed": False,
    "network_request_performed": False,
    "next_phase_unlock_performed": False,
    "order_submit_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "report_delete_performed": False,
    "report_move_performed": False,
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "signed_request_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
    "typed_confirmation_runtime_binding_performed": False,
    "typed_confirmation_secret_written": False,
    "typed_confirmation_storage_mutation_performed": False,
}


def main() -> int:
    repo_root = Path.cwd()
    missing = [path for path in EXPECTED_FILES if not (repo_root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in EXPECTED_FILES:
        if rel.endswith(".py") and (repo_root / rel).exists():
            try:
                py_compile.compile(str(repo_root / rel), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)
    payload: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "missing_files": missing,
        "written_files": EXPECTED_FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "typed_confirmation_guard_written": (repo_root / "src/tradebot/typed_confirmation_destructive_actions.py").exists(),
        "typed_confirmation_source_mutation_performed": True,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "typed_confirmation_runtime_binding_performed": False,
        "typed_confirmation_secret_written": False,
        "typed_confirmation_storage_mutation_performed": False,
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
