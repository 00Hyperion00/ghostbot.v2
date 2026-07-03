from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436637D"
PATCH_VERSION = "4B.4.3.6.6.37D"
PATCH_NAME = "Strict Config Unknown-Key Fail-Closed"
EXPECTED_FILES = [
    "README_APPLY_4B436637D.txt",
    "docs/STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_4B436637D.md",
    "src/tradebot/strict_config_unknown_key_fail_closed.py",
    "tests/test_strict_config_unknown_key_fail_closed_4B436637D.py",
    "tools/check_4B436637D_strict_config_unknown_key_fail_closed.py",
    "tools/run_4B436637D_strict_config_unknown_key_fail_closed.py",
    "tools/rollback_4B436637D_strict_config_unknown_key_fail_closed.py",
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
    "public_market_data_collection_performed": False,
    "public_observation_execution_performed": False,
    "reload_performed": False,
    "report_delete_performed": False,
    "report_move_performed": False,
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "signed_request_performed": False,
    "strict_config_runtime_loader_mutation_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def main() -> int:
    root = Path.cwd()
    compile_errors: dict[str, str] = {}
    for rel in [
        "src/tradebot/strict_config_unknown_key_fail_closed.py",
        "tools/check_4B436637D_strict_config_unknown_key_fail_closed.py",
        "tools/run_4B436637D_strict_config_unknown_key_fail_closed.py",
        "tools/rollback_4B436637D_strict_config_unknown_key_fail_closed.py",
        "tests/test_strict_config_unknown_key_fail_closed_4B436637D.py",
    ]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    missing = [rel for rel in EXPECTED_FILES if not (root / rel).exists()]
    payload: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": EXPECTED_FILES,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "strict_config_schema_guard_written": True,
        "strict_config_unknown_key_probe_written": True,
        "strict_config_source_mutation_performed": True,
        "strict_config_runtime_loader_mutation_performed": False,
        "config_runtime_reload_performed": False,
        "backup_root": "",
        "backed_up_files": [],
        "modified_files": [],
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
