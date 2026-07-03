from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436637H"
PATCH_VERSION = "4B.4.3.6.6.37H"
PATCH_NAME = "Runtime Process Lock"
WRITTEN_FILES = [
    "README_APPLY_4B436637H.txt",
    "docs/RUNTIME_PROCESS_LOCK_4B436637H.md",
    "src/tradebot/runtime_process_lock.py",
    "tests/test_runtime_process_lock_4B436637H.py",
    "tools/check_4B436637H_runtime_process_lock.py",
    "tools/run_4B436637H_runtime_process_lock.py",
    "tools/rollback_4B436637H_runtime_process_lock.py",
]

FALSE_FLAGS = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "deduplication_action_performed": False,
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
    "runtime_start_performed": False,
    "runtime_process_spawn_performed": False,
    "runtime_process_kill_performed": False,
    "process_start_performed": False,
    "process_kill_performed": False,
    "runtime_lock_file_created": False,
    "runtime_lock_file_deleted": False,
    "runtime_lock_file_mutation_performed": False,
    "runtime_lock_runtime_binding_performed": False,
    "signed_request_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}

if __name__ == "__main__":
    compile_errors: dict[str, str] = {}
    for rel in WRITTEN_FILES:
        if rel.endswith(".py"):
            try:
                py_compile.compile(rel, doraise=True)
            except Exception as exc:  # pragma: no cover
                compile_errors[rel] = str(exc)
    result = {
        "applied": not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "written_files": WRITTEN_FILES,
        "missing_files": [rel for rel in WRITTEN_FILES if not Path(rel).exists()],
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "runtime_process_lock_written": Path("src/tradebot/runtime_process_lock.py").exists(),
        "runtime_lock_source_mutation_performed": True,
        "runtime_lock_runtime_binding_performed": False,
    }
    result.update(FALSE_FLAGS)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["applied"] else 1)
