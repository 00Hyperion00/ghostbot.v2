from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436637L"
PATCH_VERSION = "4B.4.3.6.6.37L"
PATCH_NAME = "Production Hardening Final Closure"
ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "README_APPLY_4B436637L.txt",
    "docs/PRODUCTION_HARDENING_FINAL_CLOSURE_4B436637L.md",
    "src/tradebot/production_hardening_final_closure.py",
    "tests/test_production_hardening_final_closure_4B436637L.py",
    "tools/check_4B436637L_production_hardening_final_closure.py",
    "tools/run_4B436637L_production_hardening_final_closure.py",
    "tools/rollback_4B436637L_production_hardening_final_closure.py",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def main() -> int:
    missing = [path for path in EXPECTED_FILES if not (ROOT / path).exists()]
    compile_errors: dict[str, str] = {}
    for path in PY_FILES:
        target = ROOT / path
        if not target.exists():
            continue
        try:
            py_compile.compile(str(target), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[path] = str(exc)
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "applied": not missing and not compile_errors,
        "py_compile_ok": not compile_errors,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "written_files": EXPECTED_FILES,
        "modified_files": [],
        "backed_up_files": [],
        "backup_root": "",
        "production_hardening_final_closure_written": True,
        "production_hardening_final_closure_source_mutation_performed": True,
        "production_hardening_final_closure_runtime_binding_performed": False,
        "remote_tag_lookup_performed": False,
        "git_fetch_performed": False,
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
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_submit_allowed": False,
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
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
