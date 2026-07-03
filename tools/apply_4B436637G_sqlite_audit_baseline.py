from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436637G"
PATCH_VERSION = "4B.4.3.6.6.37G"
PATCH_NAME = "SQLite Audit Baseline"
WRITTEN_FILES = [
    "README_APPLY_4B436637G.txt",
    "docs/SQLITE_AUDIT_BASELINE_4B436637G.md",
    "src/tradebot/sqlite_audit_baseline.py",
    "tests/test_sqlite_audit_baseline_4B436637G.py",
    "tools/check_4B436637G_sqlite_audit_baseline.py",
    "tools/run_4B436637G_sqlite_audit_baseline.py",
    "tools/rollback_4B436637G_sqlite_audit_baseline.py",
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
    "signed_request_performed": False,
    "sqlite_backup_performed": False,
    "sqlite_file_created": False,
    "sqlite_file_deleted": False,
    "sqlite_runtime_binding_performed": False,
    "sqlite_runtime_db_mutation_performed": False,
    "sqlite_schema_migration_performed": False,
    "sqlite_write_performed": False,
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
        "sqlite_audit_baseline_written": Path("src/tradebot/sqlite_audit_baseline.py").exists(),
        "sqlite_audit_source_mutation_performed": True,
        "sqlite_audit_runtime_loader_mutation_performed": False,
        "sqlite_audit_runtime_reload_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_runtime_db_mutation_performed": False,
        "sqlite_schema_migration_performed": False,
    }
    result.update(FALSE_FLAGS)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["applied"] else 1)
