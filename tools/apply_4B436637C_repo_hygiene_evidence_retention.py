from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_ID = "4B436637C"
PATCH_VERSION = "4B.4.3.6.6.37C"
PATCH_NAME = "Repo Hygiene Evidence Retention"
EXPECTED_FILES = [
    "README_APPLY_4B436637C.txt",
    "docs/REPO_HYGIENE_EVIDENCE_RETENTION_4B436637C.md",
    "src/tradebot/repo_hygiene_evidence_retention.py",
    "tests/test_repo_hygiene_evidence_retention_4B436637C.py",
    "tools/check_4B436637C_repo_hygiene_evidence_retention.py",
    "tools/run_4B436637C_repo_hygiene_evidence_retention.py",
    "tools/rollback_4B436637C_repo_hygiene_evidence_retention.py",
]
SAFETY_FALSE = {
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
    "repo_hygiene_cleanup_performed": False,
    "report_delete_performed": False,
    "report_move_performed": False,
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
    root = Path.cwd()
    compile_errors: dict[str, str] = {}
    for rel in [
        "src/tradebot/repo_hygiene_evidence_retention.py",
        "tools/check_4B436637C_repo_hygiene_evidence_retention.py",
        "tools/run_4B436637C_repo_hygiene_evidence_retention.py",
        "tools/rollback_4B436637C_repo_hygiene_evidence_retention.py",
        "tests/test_repo_hygiene_evidence_retention_4B436637C.py",
    ]:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception as exc:  # pragma: no cover
            compile_errors[rel] = str(exc)
    missing = [rel for rel in EXPECTED_FILES if not (root / rel).exists()]
    payload: dict[str, Any] = {
        "applied": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": EXPECTED_FILES,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "repo_hygiene_policy_written": True,
        "canonical_reports_policy_mutation_performed": False,
        "patch_backup_retention_guard_mutation_performed": False,
        "backup_root": "",
        "backed_up_files": [],
        "modified_files": [],
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["applied"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
