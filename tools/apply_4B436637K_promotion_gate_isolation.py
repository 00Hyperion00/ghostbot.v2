from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436637K"
PATCH_VERSION = "4B.4.3.6.6.37K"
PATCH_NAME = "Promotion Gate Isolation"

FILES = [
    "README_APPLY_4B436637K.txt",
    "docs/PROMOTION_GATE_ISOLATION_4B436637K.md",
    "src/tradebot/promotion_gate_isolation.py",
    "tests/test_promotion_gate_isolation_4B436637K.py",
    "tools/check_4B436637K_promotion_gate_isolation.py",
    "tools/run_4B436637K_promotion_gate_isolation.py",
    "tools/rollback_4B436637K_promotion_gate_isolation.py",
]

COMPILE_TARGETS = [
    "src/tradebot/promotion_gate_isolation.py",
    "tests/test_promotion_gate_isolation_4B436637K.py",
    "tools/check_4B436637K_promotion_gate_isolation.py",
    "tools/run_4B436637K_promotion_gate_isolation.py",
    "tools/rollback_4B436637K_promotion_gate_isolation.py",
]


def main() -> int:
    root = Path.cwd()
    missing = [path for path in FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in COMPILE_TARGETS:
        target = root / rel
        if target.exists():
            try:
                py_compile.compile(str(target), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_errors[rel] = str(exc)
    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "py_compile_ok": not compile_errors,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "written_files": FILES,
        "backed_up_files": [],
        "backup_root": "",
        "modified_files": [],
        "promotion_gate_isolation_written": True,
        "promotion_gate_isolation_source_mutation_performed": True,
        "promotion_gate_mutation_performed": False,
        "promotion_state_mutation_performed": False,
        "promotion_runtime_binding_performed": False,
        "cross_phase_auto_promotion_performed": False,
        "shadow_to_paper_promotion_performed": False,
        "paper_to_live_promotion_performed": False,
        "live_real_promotion_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
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
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_performed": False,
        "next_phase_unlock_performed": False,
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
        "evidence_collection_started": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
