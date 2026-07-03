from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436637J"
PATCH_VERSION = "4B.4.3.6.6.37J"
PATCH_NAME = "Report Commit Policy"

FILES = [
    "README_APPLY_4B436637J.txt",
    "docs/REPORT_COMMIT_POLICY_4B436637J.md",
    "src/tradebot/report_commit_policy.py",
    "tests/test_report_commit_policy_4B436637J.py",
    "tools/check_4B436637J_report_commit_policy.py",
    "tools/run_4B436637J_report_commit_policy.py",
    "tools/rollback_4B436637J_report_commit_policy.py",
]

COMPILE_FILES = [
    "src/tradebot/report_commit_policy.py",
    "tests/test_report_commit_policy_4B436637J.py",
    "tools/check_4B436637J_report_commit_policy.py",
    "tools/run_4B436637J_report_commit_policy.py",
    "tools/rollback_4B436637J_report_commit_policy.py",
]


def main() -> int:
    root = Path.cwd()
    missing = [path for path in FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in COMPILE_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = f"{type(exc).__name__}: {exc}"
    result = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "missing_files": missing,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "report_commit_policy_written": True,
        "report_commit_policy_source_mutation_performed": True,
        "report_commit_policy_runtime_binding_performed": False,
        "report_commit_policy_runtime_loader_mutation_performed": False,
        "report_commit_policy_runtime_reload_performed": False,
        "historical_report_mutation_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "automatic_commit_performed": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_health_probe_performed": False,
        "runtime_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "archive_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "evidence_collection_started": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
