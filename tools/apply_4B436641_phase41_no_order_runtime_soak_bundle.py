from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436641"
PATCH_VERSION = "4B.4.3.6.6.41"
PATCH_NAME = "Phase 41 No-Order Runtime Soak Bundle"
PHASE_IDS = ["4B436641A", "4B436641B", "4B436641C", "4B436641D", "4B436641E", "4B436641F", "4B436641G", "4B436641H", "4B436641I"]
REQUIRED_FILES = [
    "README_APPLY_4B436641_PHASE41_BUNDLE.txt",
    "docs/PHASE41_NO_ORDER_RUNTIME_SOAK_BUNDLE_4B436641.md",
    "src/tradebot/paper_sandbox_phase41_common.py",
    "tests/test_phase41_no_order_runtime_soak_bundle_4B436641.py",
    "tools/check_4B436641_phase41_no_order_runtime_soak_bundle.py",
    "tools/run_4B436641_phase41_no_order_runtime_soak_bundle.py",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_targets = [
        "src/tradebot/paper_sandbox_phase41_common.py",
        "tools/check_4B436641_phase41_no_order_runtime_soak_bundle.py",
        "tools/run_4B436641_phase41_no_order_runtime_soak_bundle.py",
        "tests/test_phase41_no_order_runtime_soak_bundle_4B436641.py",
    ]
    compile_errors: dict[str, str] = {}
    for rel in compile_targets:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    payload = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "phase_ids": PHASE_IDS,
        "phase_count": len(PHASE_IDS),
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase41_bundle_source_mutation_performed": True,
        "runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "signed_request_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "destructive_cleanup_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "written_files": REQUIRED_FILES,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
