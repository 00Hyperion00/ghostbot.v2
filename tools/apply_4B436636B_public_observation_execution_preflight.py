from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436636B"
PATCH_VERSION = "4B.4.3.6.6.36B"
PATCH_NAME = "Public Observation Execution Preflight"

WRITTEN_FILES = [
    "README_APPLY_4B436636B.txt",
    "docs/PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_4B436636B.md",
    "src/tradebot/public_observation_execution_preflight.py",
    "tests/test_public_observation_execution_preflight_4B436636B.py",
    "tools/check_4B436636B_public_observation_execution_preflight.py",
    "tools/run_4B436636B_public_observation_execution_preflight.py",
    "tools/rollback_4B436636B_public_observation_execution_preflight.py",
]

NO_SUBMIT_FALSE_FLAGS = {
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
    "next_phase_unlock_performed": False,
    "order_submit_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "public_market_data_collection_performed": False,
    "public_observation_execution_performed": False,
    "public_observation_preflight_executed": False,
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
    missing_files = [rel_path for rel_path in WRITTEN_FILES if not Path(rel_path).exists()]
    compile_errors: dict[str, str] = {}
    for rel_path in WRITTEN_FILES:
        if rel_path.endswith(".py") and Path(rel_path).exists():
            try:
                py_compile.compile(rel_path, doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel_path] = str(exc)

    result = {
        "applied": not missing_files and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "written_files": WRITTEN_FILES,
        "missing_files": missing_files,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        **NO_SUBMIT_FALSE_FLAGS,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
