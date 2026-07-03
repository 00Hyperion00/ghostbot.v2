from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from tradebot.install_contract_alignment import PATCH_ID, PATCH_NAME, PATCH_VERSION, apply_install_contract_alignment

WRITTEN_FILES = [
    "README_APPLY_4B436637B.txt",
    "docs/INSTALL_CONTRACT_ALIGNMENT_4B436637B.md",
    "src/tradebot/install_contract_alignment.py",
    "tests/test_install_contract_alignment_4B436637B.py",
    "tools/check_4B436637B_install_contract_alignment.py",
    "tools/run_4B436637B_install_contract_alignment.py",
    "tools/rollback_4B436637B_install_contract_alignment.py",
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
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "signed_request_performed": False,
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

    alignment_result = apply_install_contract_alignment(Path("."))
    result = {
        "applied": not missing_files and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "written_files": WRITTEN_FILES,
        "missing_files": missing_files,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        **alignment_result,
        **NO_SUBMIT_FALSE_FLAGS,
    }
    # Preserve install-contract mutation flags from the alignment step after no-submit flags are applied.
    for key in (
        "install_contract_mutation_performed",
        "requirements_alignment_mutation_performed",
        "readme_install_contract_mutation_performed",
        "launcher_install_contract_mutation_performed",
        "modified_files",
        "backed_up_files",
        "backup_root",
    ):
        result[key] = alignment_result.get(key)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
