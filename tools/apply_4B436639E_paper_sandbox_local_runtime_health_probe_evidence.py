from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436639E"
PATCH_VERSION = "4B.4.3.6.6.39E"
PATCH_NAME = "Paper Sandbox Local Runtime Health Probe Evidence"
WRITTEN_FILES = [
    "README_APPLY_4B436639E.txt",
    "docs/PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_PROBE_EVIDENCE_4B436639E.md",
    "src/tradebot/paper_sandbox_local_runtime_health_probe_evidence.py",
    "tests/test_paper_sandbox_local_runtime_health_probe_evidence_4B436639E.py",
    "tools/apply_4B436639E_paper_sandbox_local_runtime_health_probe_evidence.py",
    "tools/check_4B436639E_paper_sandbox_local_runtime_health_probe_evidence.py",
    "tools/run_4B436639E_paper_sandbox_local_runtime_health_probe_evidence.py",
    "tools/rollback_4B436639E_paper_sandbox_local_runtime_health_probe_evidence.py",
]


def main() -> int:
    compile_errors: dict[str, str] = {}
    missing_files: list[str] = []
    for file_name in WRITTEN_FILES:
        path = Path(file_name)
        if not path.exists():
            missing_files.append(file_name)
            continue
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[file_name] = str(exc)

    applied = not missing_files and not compile_errors
    result = {
        "applied": applied,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": WRITTEN_FILES,
        "missing_files": missing_files,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "paper_sandbox_local_runtime_health_probe_evidence_written": applied,
        "paper_sandbox_local_runtime_health_probe_evidence_source_mutation_performed": applied,
        "paper_sandbox_local_runtime_health_probe_evidence_runtime_binding_performed": False,
        "health_probe_evidence_collection_performed": False,
        "runtime_health_endpoint_called": False,
        "runtime_health_probe_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "paper_runtime_start_performed": False,
        "runtime_process_start_performed": False,
        "runtime_start_performed": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "paper_order_submit_performed": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "exchange_submit_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
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
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if applied else 2


if __name__ == "__main__":
    raise SystemExit(main())
