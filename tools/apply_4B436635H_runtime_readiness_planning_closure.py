
from __future__ import annotations

import json
import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

PATCH_ID = "4B436635H"
PATCH_VERSION = "4B.4.3.6.6.35H"
PATCH_NAME = "Runtime Readiness Planning Closure"

TARGETS = [
    "README_APPLY_4B436635H.txt",
    "docs/RUNTIME_READINESS_PLANNING_CLOSURE_4B436635H.md",
    "src/tradebot/runtime_readiness_planning_closure.py",
    "tests/test_runtime_readiness_planning_closure_4B436635H.py",
    "tools/check_4B436635H_runtime_readiness_planning_closure.py",
    "tools/run_4B436635H_runtime_readiness_planning_closure.py",
    "tools/rollback_4B436635H_runtime_readiness_planning_closure.py",
]

FALSE_FLAGS = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "approved_for_paper_transition": False,
    "approved_for_runtime_overlay": False,
    "archive_execution_allowed": False,
    "archive_move_performed": False,
    "collection_authorization_unlocked": False,
    "collection_preflight_executed": False,
    "collection_runbook_executed": False,
    "collector_closure_executed": False,
    "deduplication_action_performed": False,
    "destructive_cleanup_performed": False,
    "dry_run_collector_executed": False,
    "evidence_collection_started": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "next_phase_unlock_performed": False,
    "order_submit_performed": False,
    "paper_transition_approval_performed": False,
    "paper_transition_unblocked": False,
    "phase_35_interim_seal_relaxed": False,
    "public_market_data_collection_performed": False,
    "py_compile_ok": False,
    "reload_performed": False,
    "report_delete_performed": False,
    "runtime_evidence_collection_performed": False,
    "runtime_health_probe_performed": False,
    "runtime_overlay_activated": False,
    "runtime_probe_performed": False,
    "runtime_readiness_unlock_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    repo = Path.cwd()
    payload_root = repo / "tools" / "_patch_payload_4B436635H"
    backup_root = repo / "tools" / f"_patch_backup_4B436635H_{utc_stamp()}"
    backed_up: list[str] = []
    written: list[str] = []
    modified: list[str] = []
    missing: list[str] = []

    for rel in TARGETS:
        src = payload_root / rel
        dst = repo / rel
        if not src.exists():
            missing.append(rel)
            continue
        if dst.exists():
            backup_dst = backup_root / rel
            backup_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup_dst)
            backed_up.append(rel)
            modified.append(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(rel)

    compile_errors: dict[str, str] = {}
    for rel in [
        "src/tradebot/runtime_readiness_planning_closure.py",
        "tools/check_4B436635H_runtime_readiness_planning_closure.py",
        "tools/run_4B436635H_runtime_readiness_planning_closure.py",
        "tools/rollback_4B436635H_runtime_readiness_planning_closure.py",
        "tests/test_runtime_readiness_planning_closure_4B436635H.py",
    ]:
        try:
            py_compile.compile(str(repo / rel), doraise=True)
        except Exception as exc:
            compile_errors[rel] = str(exc)

    false_flags = dict(FALSE_FLAGS)
    false_flags["py_compile_ok"] = not compile_errors
    result = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "backup_root": str(backup_root.relative_to(repo)) if backed_up else "",
        "backed_up_files": backed_up,
        "written_files": written,
        "modified_files": modified,
        "missing_files": missing,
        "compile_errors": compile_errors,
        **false_flags,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
