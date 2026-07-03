from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635D"
PATCH_VERSION = "4B.4.3.6.6.35D"
PATCH_NAME = "Collection Preflight Gate"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README_APPLY_4B436635D.txt",
    "docs/COLLECTION_PREFLIGHT_GATE_4B436635D.md",
    "src/tradebot/collection_preflight_gate.py",
    "tests/test_collection_preflight_gate_4B436635D.py",
    "tools/check_4B436635D_collection_preflight_gate.py",
    "tools/run_4B436635D_collection_preflight_gate.py",
    "tools/rollback_4B436635D_collection_preflight_gate.py",
]
PY_FILES = [path for path in FILES if path.endswith(".py")]
FALSE_FLAGS = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "collection_preflight_executed": False,
    "collection_runbook_executed": False,
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
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "reload_performed": False,
    "report_delete_performed": False,
    "runtime_overlay_activated": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def main() -> int:
    missing = [path for path in FILES if not (ROOT / path).exists()]
    compile_errors: dict[str, str] = {}
    if not missing:
        for rel in PY_FILES:
            try:
                py_compile.compile(str(ROOT / rel), doraise=True)
            except Exception as exc:
                compile_errors[rel] = str(exc)
    result: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "missing_files": missing,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "py_compile_ok": not compile_errors and not missing,
        "compile_errors": compile_errors,
        **FALSE_FLAGS,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
