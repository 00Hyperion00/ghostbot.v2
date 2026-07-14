from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PATCH_ID = "4B436661"
PATCH_VERSION = "4B.4.3.6.6.61"
PATCH_NAME = "Release Audit / Repository Hygiene / Pytest Collection Isolation"

DECISION = (
    "RELEASE_AUDIT_REPOSITORY_HYGIENE_PYTEST_COLLECTION_ISOLATION_READY_"
    "CANONICAL_TEST_DISCOVERY_CONFIGURED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_"
    "NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

FINAL_PHASE_DECISION = (
    "RELEASE_AUDIT_REPOSITORY_HYGIENE_CLOSURE_READY_PHASE61_CLOSED_"
    "PYTEST_COLLECTION_ISOLATED_LEGACY_DRIFT_REPORTED_NO_PAPER_SUBMIT_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

NEXT_PHASE = "4B.4.3.6.6.62A"
NEXT_PHASE_NAME = "Patch Artifact Consolidation / Repository Cleanup Review"

IGNORED_COLLECTION_DIR_PATTERNS: tuple[str, ...] = (
    "_patch_backup*",
    "_patch_payload*",
    "legacy_patches",
)

CANONICAL_TESTPATHS: tuple[str, ...] = ("tests",)

LEGACY_API_DRIFT_SYMBOLS: tuple[str, ...] = (
    "SQLITE_MIRROR_REQUIRED_DECISION",
    "build_production_hardening_snapshot",
    "OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY",
)

PYTEST_INI_CONTENT = """[pytest]
testpaths =
    tests
python_files =
    test_*.py
norecursedirs =
    .git
    .hg
    .svn
    .tox
    .venv
    venv
    env
    build
    dist
    .eggs
    *.egg
    _patch_backup*
    _patch_payload*
    legacy_patches
addopts =
    -ra
    --import-mode=importlib
    --ignore-glob=tools/_patch_backup_*
    --ignore-glob=tools/_patch_payload_*
    --ignore=legacy_patches
    --ignore-glob=**/_patch_backup_*
    --ignore-glob=**/_patch_payload_*
    --ignore-glob=**/legacy_patches
"""

SAFETY_LOCKS: dict[str, bool] = {
    "actual_evidence_accepted_by_patch": False,
    "actual_evidence_ingested_by_patch": False,
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "dry_run_execution_performed_by_patch": False,
    "evidence_collection_performed_by_patch": False,
    "exchange_submit_allowed": False,
    "exchange_submit_enabled_by_patch": False,
    "exchange_submit_performed": False,
    "live_real_approved_by_patch": False,
    "live_real_submit_allowed": False,
    "network_order_submit_allowed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "network_submit_allowed": False,
    "order_path_opened_by_patch": False,
    "paper_order_path_opened_by_patch": False,
    "paper_order_submit_allowed": False,
    "paper_order_submit_performed": False,
    "paper_runtime_start_performed": False,
    "paper_submit_allowed": False,
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_submit_performed_by_patch": False,
    "paper_trading_evidence_collected_by_patch": False,
    "paper_trading_soak_accepted_by_patch": False,
    "paper_trading_soak_started_by_patch": False,
    "private_api_access_allowed": False,
    "private_api_access_performed": False,
    "reload_performed": False,
    "runtime_health_endpoint_called": False,
    "runtime_health_probe_performed": False,
    "runtime_metrics_collection_performed": False,
    "runtime_overlay_activated": False,
    "runtime_process_started": False,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_performed": False,
    "runtime_started_by_patch": False,
    "signed_request_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}


@dataclass(frozen=True)
class CollectionIsolationFinding:
    path: str
    pattern: str
    excluded_by_pytest_config: bool


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_skipped_walk_dir(dirname: str) -> bool:
    return dirname in {".git", ".hg", ".svn", ".tox", ".venv", "venv", "env", "build", "dist", "__pycache__"}


def _matches_collection_ignore(name: str) -> str | None:
    for pattern in IGNORED_COLLECTION_DIR_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return pattern
    return None


def discover_legacy_collection_directories(project_root: Path) -> list[CollectionIsolationFinding]:
    root = project_root.resolve()
    findings: list[CollectionIsolationFinding] = []
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [d for d in dirs if not _is_skipped_walk_dir(d)]
        for dirname in list(dirs):
            matched = _matches_collection_ignore(dirname)
            if matched is None:
                continue
            full_path = current_path / dirname
            try:
                rel = full_path.relative_to(root).as_posix()
            except ValueError:
                rel = full_path.as_posix()
            findings.append(
                CollectionIsolationFinding(
                    path=rel,
                    pattern=matched,
                    excluded_by_pytest_config=True,
                )
            )
    return sorted(findings, key=lambda item: item.path)


def _digest_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected_pytest_ini_content() -> str:
    return PYTEST_INI_CONTENT


def read_pytest_ini(project_root: Path) -> str | None:
    path = project_root / "pytest.ini"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def verify_pytest_collection_config(project_root: Path) -> dict[str, Any]:
    content = read_pytest_ini(project_root)
    required_tokens = (
        "testpaths",
        "tests",
        "norecursedirs",
        "_patch_backup*",
        "_patch_payload*",
        "legacy_patches",
        "--import-mode=importlib",
        "--ignore-glob=tools/_patch_backup_*",
        "--ignore-glob=tools/_patch_payload_*",
        "--ignore=legacy_patches",
        "--ignore-glob=**/_patch_backup_*",
        "--ignore-glob=**/_patch_payload_*",
        "--ignore-glob=**/legacy_patches",
    )
    missing = [token for token in required_tokens if content is None or token not in content]
    return {
        "pytest_ini_present": content is not None,
        "pytest_ini_path": str((project_root / "pytest.ini").resolve()),
        "pytest_ini_missing_required_tokens": missing,
        "canonical_test_discovery_configured": not missing,
        "duplicate_test_module_mismatch_prevention_configured": content is not None and "--import-mode=importlib" in content,
        "legacy_patch_collection_isolated": content is not None
        and all(token in content for token in ("_patch_backup*", "_patch_payload*", "legacy_patches")),
    }


def build_release_audit_snapshot(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else Path.cwd()
    root = root.resolve()
    config_status = verify_pytest_collection_config(root)
    collection_findings = discover_legacy_collection_directories(root)
    safety_violations = [key for key, value in SAFETY_LOCKS.items() if value]

    payload: dict[str, Any] = {
        "ok": config_status["canonical_test_discovery_configured"] and not safety_violations,
        "status": "READY" if config_status["canonical_test_discovery_configured"] and not safety_violations else "BLOCKED",
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "phase": 61,
        "phase_61_closed": config_status["canonical_test_discovery_configured"] and not safety_violations,
        "decision": DECISION if config_status["canonical_test_discovery_configured"] and not safety_violations else "PHASE61_BLOCKED_PYTEST_COLLECTION_CONFIG_INCOMPLETE",
        "final_phase_decision": FINAL_PHASE_DECISION if config_status["canonical_test_discovery_configured"] and not safety_violations else "PHASE61_BLOCKED_RELEASE_AUDIT_HYGIENE_INCOMPLETE",
        "generated_at_utc": utc_stamp(),
        "project_root": str(root),
        "canonical_testpaths": list(CANONICAL_TESTPATHS),
        "ignored_collection_dir_patterns": list(IGNORED_COLLECTION_DIR_PATTERNS),
        "pytest_config": config_status,
        "legacy_collection_directories_detected": [asdict(item) for item in collection_findings],
        "legacy_collection_directory_count": len(collection_findings),
        "legacy_api_drift_report_only": True,
        "legacy_api_drift_symbols_reported": list(LEGACY_API_DRIFT_SYMBOLS),
        "legacy_api_drift_fix_performed_by_patch": False,
        "duplicate_test_module_mismatch_cleanup_performed_by_patch": False,
        "duplicate_test_module_mismatch_prevention_configured": config_status["duplicate_test_module_mismatch_prevention_configured"],
        "canonical_test_discovery_enabled": config_status["canonical_test_discovery_configured"],
        "pytest_collection_isolation_enabled": config_status["legacy_patch_collection_isolated"],
        "release_audit_only": True,
        "repository_cleanup_performed_by_patch": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "destructive_cleanup_performed": False,
        "manual_operator_review_required_before_paper_submit": True,
        "manual_governance_required_for_any_live_action": True,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "final_safety_violation_count": len(safety_violations),
        "final_safety_violations": safety_violations,
        **SAFETY_LOCKS,
    }
    payload["report_digest"] = _digest_json({k: v for k, v in payload.items() if k not in {"generated_at_utc", "report_digest"}})
    return payload


def write_release_audit_report(reports_dir: str | Path, project_root: str | Path | None = None) -> dict[str, Any]:
    payload = build_release_audit_snapshot(project_root)
    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = str(payload.get("status", "unknown")).lower()
    report_path = out_dir / f"{PATCH_ID}_release_audit_pytest_collection_hygiene_{utc_stamp()}_{status}.json"
    payload["report_path"] = str(report_path)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_digest"] = _digest_json({k: v for k, v in payload.items() if k not in {"generated_at_utc", "report_digest", "report_path"}})
    return payload


def main() -> None:
    print(json.dumps(build_release_audit_snapshot(), sort_keys=True))


if __name__ == "__main__":
    main()
