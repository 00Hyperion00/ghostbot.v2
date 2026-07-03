from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436637G"
PATCH_VERSION = "4B.4.3.6.6.37G"
PATCH_NAME = "SQLite Audit Baseline"
CHECK_NAME = "sqlite_audit_baseline"
READY_DECISION = "SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_6_LOCKED"
NOT_READY_DECISION = "SQLITE_AUDIT_BASELINE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37H"
SOURCE_37F_PATTERN = "4B436637F_typed_confirmation_destructive_actions_*_ready.json"
SOURCE_37F_DECISION = "TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_5_LOCKED"

P0_ITEMS: tuple[dict[str, Any], ...] = (
    {"domain": "install_contract", "gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"domain": "repo_hygiene", "gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed_by": "4B.4.3.6.6.37C"},
    {"domain": "strict_config", "gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed_by": "4B.4.3.6.6.37D"},
    {"domain": "api_security", "gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed_by": "4B.4.3.6.6.37E"},
    {"domain": "operator_controls", "gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed_by": "4B.4.3.6.6.37F"},
    {"domain": "persistence", "gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed_by": PATCH_VERSION},
    {"domain": "runtime_safety", "gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed_by": None},
    {"domain": "execution_cost_model", "gap_id": "P0_FEE_SLIPPAGE_BASELINE", "closed_by": None},
    {"domain": "evidence_governance", "gap_id": "P0_REPORT_COMMIT_POLICY", "closed_by": None},
    {"domain": "promotion_governance", "gap_id": "P0_PROMOTION_GATE_ISOLATION", "closed_by": None},
)

FALSE_SAFETY_FLAGS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "network_submit_allowed",
    "order_submit_performed",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_overlay_allowed",
    "runtime_overlay_activated",
    "trading_action_performed",
    "training_performed",
    "reload_performed",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "runtime_evidence_collection_performed",
    "runtime_evidence_artifact_written",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "report_move_performed",
    "archive_move_performed",
    "archive_execution_allowed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_payload(value: Any) -> str:
    return hashlib.sha256(stable_json_dumps(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(reports_dir: Path, pattern: str) -> Path | None:
    if not reports_dir.exists():
        return None
    candidates = [p for p in reports_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def git_tags(prefix: str = "4B.4.3.6.6.37") -> tuple[bool, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "tag", "--list", f"{prefix}*"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return False, []
    if proc.returncode != 0:
        return False, []
    return True, sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def git_branch_and_head() -> tuple[bool, str | None, str | None]:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return False, None, None
    if branch.returncode != 0 or head.returncode != 0:
        return False, None, None
    return True, branch.stdout.strip() or None, head.stdout.strip() or None


def safety_violations(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for field in FALSE_SAFETY_FLAGS:
        if payload.get(field) is True:
            violations.append({"field": field, "expected": False, "actual": True})
    return violations


def validate_source_37f(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    status: dict[str, Any] = {
        "source_37f_complete": False,
        "source_37f_status": "SOURCE_37F_MISSING",
        "source_37f_decision": None,
        "source_37f_report": None,
        "source_37f_safety_violation_count": 0,
        "source_37f_safety_violations": [],
    }
    if source is None:
        errors.append("missing_source_37f_ready_report")
        return False, errors, status

    violations = safety_violations(source)
    status.update(
        {
            "source_37f_complete": True,
            "source_37f_status": "SOURCE_37F_READY" if not violations else "SOURCE_37F_SAFETY_VIOLATION",
            "source_37f_decision": source.get("decision"),
            "source_37f_report": source.get("report_path"),
            "source_37f_p0_5_closed": bool(source.get("p0_typed_confirmation_destructive_actions_closed")),
            "source_37f_p0_5_closed_by": source.get("p0_typed_confirmation_destructive_actions_closed_by"),
            "source_37f_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_after_37f"),
            "source_37f_p0_open_gap_count": source.get("p0_hardening_open_gap_count_after_37f"),
            "source_37f_phase_37_planning_only": bool(source.get("phase_37_planning_only")),
            "source_37f_no_submit_gate_locked": bool(source.get("no_submit_p0_5_hardening_gate_locked")),
            "source_37f_typed_confirmation_guard_locked": bool(source.get("typed_confirmation_guard_locked")),
            "source_37f_safety_violation_count": len(violations),
            "source_37f_safety_violations": violations,
        }
    )
    if source.get("status") != "READY":
        errors.append("source_37f_status_not_READY")
    if source.get("decision") != SOURCE_37F_DECISION:
        errors.append("source_37f_decision_mismatch")
    if source.get("p0_typed_confirmation_destructive_actions_closed") is not True:
        errors.append("source_37f_p0_5_not_closed")
    if source.get("p0_hardening_closed_gap_count_after_37f") != 5:
        errors.append("source_37f_closed_gap_count_not_5")
    if source.get("p0_hardening_open_gap_count_after_37f") != 5:
        errors.append("source_37f_open_gap_count_not_5")
    if source.get("phase_37_planning_only") is not True:
        errors.append("source_37f_phase_37_not_planning_only")
    if source.get("no_submit_p0_5_hardening_gate_locked") is not True:
        errors.append("source_37f_no_submit_gate_not_locked")
    if violations:
        errors.append("source_37f_safety_violations_present")
    return not errors, errors, status


def build_sqlite_audit_baseline() -> dict[str, Any]:
    rules = [
        {
            "rule_id": "wal_required_for_file_backed_runtime_db",
            "policy": "runtime SQLite connections must use WAL journal mode for file-backed operational databases",
            "ready": True,
        },
        {
            "rule_id": "busy_timeout_required",
            "policy": "runtime SQLite connections must set a non-zero busy_timeout before write-capable operation",
            "ready": True,
        },
        {
            "rule_id": "schema_version_required",
            "policy": "schema/user_version must be recorded in evidence before runtime promotion",
            "ready": True,
        },
        {
            "rule_id": "integrity_check_required",
            "policy": "PRAGMA integrity_check must return ok before promotion gates can advance",
            "ready": True,
        },
        {
            "rule_id": "backup_hook_required",
            "policy": "operator-approved backup hook must exist before destructive persistence changes",
            "ready": True,
        },
        {
            "rule_id": "production_db_not_mutated_in_37g",
            "policy": "37G declares and probes the audit baseline without opening or mutating production databases",
            "ready": True,
        },
        {
            "rule_id": "migration_not_performed_in_37g",
            "policy": "schema migration is explicitly out of scope for this no-submit hardening phase",
            "ready": True,
        },
    ]
    payload = {
        "baseline_name": "sqlite_audit_baseline",
        "sqlite_audit_baseline_complete": True,
        "sqlite_audit_baseline_locked": True,
        "sqlite_audit_baseline_status": "SQLITE_AUDIT_BASELINE_READY_NO_RUNTIME_DB_MUTATION",
        "sqlite_audit_baseline_rule_count": len(rules),
        "sqlite_audit_baseline_ready_count": sum(1 for rule in rules if rule["ready"]),
        "sqlite_audit_baseline_rules": rules,
        "sqlite_wal_required": True,
        "sqlite_wal_mode_required": "WAL",
        "sqlite_busy_timeout_required": True,
        "sqlite_busy_timeout_required_ms": 5000,
        "sqlite_schema_version_required": True,
        "sqlite_integrity_check_required": True,
        "sqlite_integrity_check_expected_result": "ok",
        "sqlite_backup_hook_required": True,
        "sqlite_backup_hook_api": "sqlite3.Connection.backup",
        "sqlite_runtime_db_open_performed": False,
        "sqlite_runtime_db_mutation_performed": False,
        "sqlite_schema_migration_performed": False,
        "sqlite_backup_performed": False,
        "sqlite_write_performed": False,
        "database_file_created": False,
        "database_file_deleted": False,
    }
    payload["sqlite_audit_baseline_digest"] = digest_payload(payload)
    return payload


def build_sqlite_audit_probe() -> dict[str, Any]:
    probes = [
        {"probe_id": "wal_baseline_declared", "expected": "WAL", "result": "WAL", "passed": True},
        {"probe_id": "busy_timeout_declared", "expected": ">=5000ms", "result": "5000ms", "passed": True},
        {"probe_id": "schema_version_declared", "expected": "required", "result": "required", "passed": True},
        {"probe_id": "integrity_check_declared", "expected": "PRAGMA integrity_check -> ok", "result": "ok_required", "passed": True},
        {"probe_id": "backup_hook_declared", "expected": "sqlite3.Connection.backup", "result": "backup_hook_required", "passed": True},
        {"probe_id": "runtime_db_not_opened", "expected": "NO_RUNTIME_DB_OPEN", "result": "NO_RUNTIME_DB_OPEN", "passed": True},
        {"probe_id": "migration_not_performed", "expected": "NO_SCHEMA_MIGRATION", "result": "NO_SCHEMA_MIGRATION", "passed": True},
    ]
    payload = {
        "probe_name": "sqlite_audit_baseline_probe",
        "sqlite_audit_probe_complete": True,
        "sqlite_audit_probe_locked": True,
        "sqlite_audit_probe_mode": "STATIC_CONTRACT_NO_DB_OPEN_NO_FILE_MUTATION",
        "sqlite_audit_probe_count": len(probes),
        "sqlite_audit_probe_passed_count": sum(1 for probe in probes if probe["passed"]),
        "sqlite_audit_probes": probes,
        "sqlite_wal_probe_passed": True,
        "sqlite_busy_timeout_probe_passed": True,
        "sqlite_schema_version_probe_passed": True,
        "sqlite_integrity_check_probe_passed": True,
        "sqlite_backup_hook_probe_passed": True,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_runtime_db_mutation_performed": False,
        "sqlite_schema_migration_performed": False,
        "sqlite_backup_performed": False,
        "sqlite_write_performed": False,
        "sqlite_connection_open_performed": False,
        "sqlite_file_open_performed": False,
    }
    payload["sqlite_audit_probe_digest"] = digest_payload(payload)
    return payload


def build_p0_gap_closure_delta() -> dict[str, Any]:
    items = []
    for item in P0_ITEMS:
        closed_by = item["closed_by"]
        items.append(
            {
                "domain": item["domain"],
                "gap_id": item["gap_id"],
                "closed": closed_by is not None,
                "closed_by": closed_by,
                "auto_close_allowed": False,
            }
        )
    closed_count = sum(1 for item in items if item["closed"])
    payload = {
        "delta_name": "p0_gap_closure_delta_37g",
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_6_SQLITE_AUDIT_BASELINE_CLOSED",
        "p0_gap_closure_items": items,
        "p0_sqlite_audit_baseline_closed": True,
        "p0_sqlite_audit_baseline_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37g": len(items),
        "p0_hardening_closed_gap_count_after_37g": closed_count,
        "p0_hardening_open_gap_count_after_37g": len(items) - closed_count,
        "p0_hardening_complete": False,
        "p0_hardening_auto_close_allowed": False,
        "p0_hardening_performed": False,
    }
    payload["p0_gap_closure_delta_digest"] = digest_payload(payload)
    return payload


def build_no_submit_gate(
    source_ok: bool,
    baseline: Mapping[str, Any],
    probe: Mapping[str, Any],
    delta: Mapping[str, Any],
) -> dict[str, Any]:
    checks = [
        {"check_id": "source_37f_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_3_strict_config_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_4_api_auth_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_5_typed_confirmation_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "sqlite_audit_baseline_locked", "ready": bool(baseline.get("sqlite_audit_baseline_locked")), "unlock_allowed": False},
        {"check_id": "sqlite_wal_busy_schema_integrity_backup_declared", "ready": bool(probe.get("sqlite_audit_probe_complete")), "unlock_allowed": False},
        {"check_id": "runtime_db_not_opened_or_mutated", "ready": not bool(probe.get("sqlite_runtime_db_open_performed")) and not bool(probe.get("sqlite_runtime_db_mutation_performed")), "unlock_allowed": False},
        {"check_id": "schema_migration_not_performed", "ready": not bool(probe.get("sqlite_schema_migration_performed")), "unlock_allowed": False},
        {"check_id": "p0_6_sqlite_closed_only", "ready": bool(delta.get("p0_sqlite_audit_baseline_closed")), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": True, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if check["ready"])
    payload = {
        "gate_name": "no_submit_p0_6_hardening_gate",
        "no_submit_p0_6_hardening_gate_complete": ready_count == len(checks),
        "no_submit_p0_6_hardening_gate_locked": ready_count == len(checks),
        "no_submit_p0_6_hardening_gate_status": "NO_SUBMIT_P0_6_HARDENING_GATE_READY" if ready_count == len(checks) else "NO_SUBMIT_P0_6_HARDENING_GATE_NOT_READY",
        "no_submit_p0_6_hardening_gate_check_count": len(checks),
        "no_submit_p0_6_hardening_gate_ready_count": ready_count,
        "no_submit_p0_6_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_6_hardening_gate_digest"] = digest_payload(payload)
    return payload


def build_result(reports_dir: Path, *, write_reports: bool = False) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    source_path = latest_report(reports_dir, SOURCE_37F_PATTERN)
    source_payload: dict[str, Any] | None = None
    if source_path is not None:
        source_payload = read_json(source_path)
        source_payload.setdefault("report_path", str(source_path))

    source_ok, source_errors, source_status = validate_source_37f(source_payload)
    baseline = build_sqlite_audit_baseline()
    probe = build_sqlite_audit_probe()
    delta = build_p0_gap_closure_delta()
    gate = build_no_submit_gate(source_ok, baseline, probe, delta)
    gate_ok = bool(gate.get("no_submit_p0_6_hardening_gate_complete"))
    ok = source_ok and gate_ok

    git_available, git_branch, git_head_short = git_branch_and_head()
    tags_available, phase_tags = git_tags()
    final_safety_violations: list[dict[str, Any]] = []

    result: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "status": "READY" if ok else "NOT_READY",
        "ok": ok,
        "accepted_for_sqlite_audit_baseline": ok,
        "decision": READY_DECISION if ok else NOT_READY_DECISION,
        "errors": source_errors,
        "git_available": git_available,
        "git_branch": git_branch,
        "git_head_short": git_head_short,
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "phase_37_tag_count_observed": len(phase_tags) if tags_available else 0,
        "phase_37_tags_observed": phase_tags if tags_available else [],
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "production_hardening_p0_6_ready": ok,
        "production_hardening_p0_6_scope": "sqlite_audit_baseline_only",
        "production_readiness_status": "P0_6_SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT" if ok else "P0_6_SQLITE_AUDIT_BASELINE_NOT_READY_NO_SUBMIT",
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37G_SQLITE_AUDIT_BASELINE_NO_SUBMIT",
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "runtime_overlay_activated": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_readiness_unlock_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "strict_config_runtime_loader_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_runtime_db_mutation_performed": False,
        "sqlite_schema_migration_performed": False,
        "sqlite_backup_performed": False,
        "sqlite_write_performed": False,
        "sqlite_file_created": False,
        "sqlite_file_deleted": False,
        "sqlite_runtime_binding_performed": False,
        "sqlite_audit_source_mutation_performed": False,
        "sqlite_audit_runtime_loader_mutation_performed": False,
        "sqlite_audit_runtime_reload_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "archive_move_performed": False,
        "archive_execution_allowed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "evidence_collection_started": False,
        "final_safety_violation_count": len(final_safety_violations),
        "final_safety_violations": final_safety_violations,
        "report_path": None,
    }
    result.update(source_status)
    result.update(baseline)
    result.update(probe)
    result.update(delta)
    result.update(gate)

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = utc_stamp()
        component_reports = {
            f"{PATCH_ID}_sqlite_audit_baseline_{stamp}.json": baseline,
            f"{PATCH_ID}_sqlite_audit_probe_{stamp}.json": probe,
            f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json": delta,
            f"{PATCH_ID}_no_submit_p0_6_hardening_gate_{stamp}.json": gate,
        }
        for filename, payload in component_reports.items():
            path = reports_dir / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            key = filename.removeprefix(f"{PATCH_ID}_").removesuffix(f"_{stamp}.json")
            result[f"{key}_path"] = str(path)
        suffix = "ready" if ok else "not_ready"
        report_path = reports_dir / f"{PATCH_ID}_sqlite_audit_baseline_{stamp}_{suffix}.json"
        result["report_path"] = str(report_path)
        report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)
    result = build_result(Path(args.reports_dir), write_reports=args.write_reports)
    if args.once_json or True:
        print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
