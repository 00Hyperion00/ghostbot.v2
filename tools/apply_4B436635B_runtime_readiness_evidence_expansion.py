from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635B"
PATCH_VERSION = "4B.4.3.6.6.35B"
PATCH_NAME = "Runtime Readiness Evidence Expansion"

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README_APPLY_4B436635B.txt",
    "docs/RUNTIME_READINESS_EVIDENCE_EXPANSION_4B436635B.md",
    "src/tradebot/runtime_readiness_evidence_expansion.py",
    "tests/test_runtime_readiness_evidence_expansion_4B436635B.py",
    "tools/check_4B436635B_runtime_readiness_evidence_expansion.py",
    "tools/run_4B436635B_runtime_readiness_evidence_expansion.py",
    "tools/rollback_4B436635B_runtime_readiness_evidence_expansion.py",
]
PYTHON_FILES = [item for item in FILES if item.endswith(".py")]

FALSE_FLAGS = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "deduplication_action_performed": False,
    "destructive_cleanup_performed": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "next_phase_unlock_performed": False,
    "order_submit_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "report_delete_performed": False,
    "runtime_overlay_activated": False,
    "runtime_readiness_unlock_performed": False,
    "runtime_evidence_collection_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def main() -> int:
    missing = [item for item in FILES if not (ROOT / item).exists()]
    compile_errors: dict[str, str] = {}
    for item in PYTHON_FILES:
        path = ROOT / item
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[item] = str(exc)

    result: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "missing_files": missing,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        **FALSE_FLAGS,
    }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
