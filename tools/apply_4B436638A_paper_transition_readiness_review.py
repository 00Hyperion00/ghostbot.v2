from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436638A"
PATCH_VERSION = "4B.4.3.6.6.38A"
PATCH_NAME = "Paper Transition Readiness Review"

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README_APPLY_4B436638A.txt",
    "docs/PAPER_TRANSITION_READINESS_REVIEW_4B436638A.md",
    "src/tradebot/paper_transition_readiness_review.py",
    "tests/test_paper_transition_readiness_review_4B436638A.py",
    "tools/check_4B436638A_paper_transition_readiness_review.py",
    "tools/run_4B436638A_paper_transition_readiness_review.py",
    "tools/rollback_4B436638A_paper_transition_readiness_review.py",
]
COMPILE_FILES = [p for p in FILES if p.endswith(".py")]


def main() -> int:
    missing = [p for p in FILES if not (ROOT / p).exists()]
    compile_errors: dict[str, str] = {}
    for rel in COMPILE_FILES:
        path = ROOT / rel
        if path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)
    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "written_files": FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "production_hardening_final_closure_source_mutation_performed": False,
        "paper_transition_readiness_review_written": True,
        "paper_transition_source_mutation_performed": True,
        "paper_transition_runtime_binding_performed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "live_transition_approval_performed": False,
        "exchange_submit_approval_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
