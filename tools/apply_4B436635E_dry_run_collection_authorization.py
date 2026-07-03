from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436635E"
PATCH_VERSION = "4B.4.3.6.6.35E"
PATCH_NAME = "Dry-Run Collection Authorization"

FILES = [
    "README_APPLY_4B436635E.txt",
    "docs/DRY_RUN_COLLECTION_AUTHORIZATION_4B436635E.md",
    "src/tradebot/dry_run_collection_authorization.py",
    "tests/test_dry_run_collection_authorization_4B436635E.py",
    "tools/check_4B436635E_dry_run_collection_authorization.py",
    "tools/run_4B436635E_dry_run_collection_authorization.py",
    "tools/rollback_4B436635E_dry_run_collection_authorization.py",
]

PY_FILES = [path for path in FILES if path.endswith(".py")]

FALSE_FLAGS = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "collection_authorization_unlocked": False,
    "collection_preflight_executed": False,
    "collection_runbook_executed": False,
    "deduplication_action_performed": False,
    "destructive_cleanup_performed": False,
    "dry_run_collection_authorization_performed": False,
    "evidence_collection_started": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "next_phase_unlock_performed": False,
    "order_submit_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "public_market_data_collection_performed": False,
    "reload_performed": False,
    "report_delete_performed": False,
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def main() -> int:
    root = Path.cwd()
    missing_files: list[str] = []
    compile_errors: dict[str, str] = {}
    for rel in FILES:
        if not (root / rel).exists():
            missing_files.append(rel)
    for rel in PY_FILES:
        path = root / rel
        if path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)
    result = {
        "applied": not missing_files and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "missing_files": missing_files,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
    }
    result.update(FALSE_FLAGS)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
