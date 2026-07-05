from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436638D"
PATCH_VERSION = "4B.4.3.6.6.38D"
PATCH_NAME = "Paper Sandbox Operator Approval Ledger"

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "README_APPLY_4B436638D.txt",
    "docs/PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_4B436638D.md",
    "src/tradebot/paper_sandbox_operator_approval_ledger.py",
    "tests/test_paper_sandbox_operator_approval_ledger_4B436638D.py",
    "tools/check_4B436638D_paper_sandbox_operator_approval_ledger.py",
    "tools/run_4B436638D_paper_sandbox_operator_approval_ledger.py",
    "tools/rollback_4B436638D_paper_sandbox_operator_approval_ledger.py",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def main() -> int:
    missing_files = [path for path in EXPECTED_FILES if not (ROOT / path).exists()]
    compile_errors: dict[str, str] = {}
    for relative in PY_FILES:
        path = ROOT / relative
        if path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[relative] = str(exc)

    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing_files and not compile_errors,
        "missing_files": missing_files,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "written_files": EXPECTED_FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "paper_sandbox_operator_approval_ledger_written": True,
        "operator_approval_ledger_source_mutation_performed": True,
        "operator_approval_ledger_runtime_binding_performed": False,
        "operator_approval_ledger_mutation_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_submit_allowed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
