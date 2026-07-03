from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436637E"
PATCH_VERSION = "4B.4.3.6.6.37E"
PATCH_NAME = "API Auth Destructive Endpoint Guard"
EXPECTED_FILES = [
    "README_APPLY_4B436637E.txt",
    "docs/API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_4B436637E.md",
    "src/tradebot/api_auth_destructive_endpoint_guard.py",
    "tests/test_api_auth_destructive_endpoint_guard_4B436637E.py",
    "tools/check_4B436637E_api_auth_destructive_endpoint_guard.py",
    "tools/run_4B436637E_api_auth_destructive_endpoint_guard.py",
    "tools/rollback_4B436637E_api_auth_destructive_endpoint_guard.py",
]

SAFETY_FALSE = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "deduplication_action_performed": False,
    "destructive_cleanup_performed": False,
    "destructive_endpoint_runtime_binding_performed": False,
    "destructive_endpoint_execution_performed": False,
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
    "token_secret_written": False,
    "token_storage_mutation_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
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
        "api_auth_guard_written": (repo_root / "src/tradebot/api_auth_destructive_endpoint_guard.py").exists(),
        "api_auth_source_mutation_performed": True,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "api_auth_runtime_loader_mutation_performed": False,
        "api_auth_runtime_reload_performed": False,
        "token_storage_mutation_performed": False,
        "token_secret_written": False,
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
