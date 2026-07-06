from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436641A"
PATCH_VERSION = "4B.4.3.6.6.41A"
PATCH_NAME = "Paper Sandbox No-Order Runtime Soak Planning"
REQUIRED_FILES = [
    "README_APPLY_4B436641A.txt",
    "docs/PAPER_SANDBOX_NO_ORDER_RUNTIME_SOAK_PLANNING_4B436641A.md",
    "src/tradebot/paper_sandbox_no_order_runtime_soak_planning.py",
    "tests/test_paper_sandbox_no_order_runtime_soak_planning_4B436641A.py",
    "tools/apply_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py",
    "tools/check_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py",
    "tools/run_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py",
    "tools/rollback_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in ["src/tradebot/paper_sandbox_no_order_runtime_soak_planning.py", "tools/check_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py", "tools/run_4B436641A_paper_sandbox_no_order_runtime_soak_planning.py", "tests/test_paper_sandbox_no_order_runtime_soak_planning_4B436641A.py"]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    payload = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "phase41_source_mutation_performed": True,
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
