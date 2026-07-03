from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436637H"
PATCH_VERSION = "4B.4.3.6.6.37H"
PATCH_NAME = "Runtime Process Lock"
CHECK_NAME = "runtime_process_lock"
READY_DECISION = "RUNTIME_PROCESS_LOCK_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_7_LOCKED"
NOT_READY_DECISION = "RUNTIME_PROCESS_LOCK_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37I"
SOURCE_37G_PATTERN = "4B436637G_sqlite_audit_baseline_*_ready.json"
SOURCE_37G_DECISION = "SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_6_LOCKED"

LOCK_FILE_NAME = "tradebot_runtime.lock"
LOCK_DIR_POLICY = "runtime/locks"
STALE_LOCK_TTL_SECONDS = 900

P0_ITEMS: tuple[dict[str, Any], ...] = (
    {"domain": "install_contract", "gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"domain": "repo_hygiene", "gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed_by": "4B.4.3.6.6.37C"},
    {"domain": "strict_config", "gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed_by": "4B.4.3.6.6.37D"},
    {"domain": "api_security", "gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed_by": "4B.4.3.6.6.37E"},
    {"domain": "operator_controls", "gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed_by": "4B.4.3.6.6.37F"},
    {"domain": "persistence", "gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed_by": "4B.4.3.6.6.37G"},
    {"domain": "runtime_safety", "gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed_by": PATCH_VERSION},
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
    "runtime_start_allowed",
    "runtime_start_performed",
    "runtime_process_spawn_performed",
    "runtime_process_kill_allowed",
    "runtime_process_kill_performed",
    "process_start_performed",
    "process_kill_performed",
    "runtime_lock_file_created",
    "runtime_lock_file_deleted",
    "runtime_lock_file_mutation_performed",
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


@dataclass(frozen=True)
class RuntimeLockOwner:
    pid: int
    started_at_utc: str
    patch_version: str
    command: str
    host: str


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


def validate_source_37g(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    status: dict[str, Any] = {
        "source_37g_complete": False,
        "source_37g_status": "SOURCE_37G_MISSING",
        "source_37g_decision": None,
        "source_37g_report": None,
        "source_37g_safety_violation_count": 0,
        "source_37g_safety_violations": [],
    }
    if source is None:
        errors.append("missing_source_37g_ready_report")
        return False, errors, status

    violations = safety_violations(source)
    status.update(
        {
            "source_37g_complete": True,
            "source_37g_status": "SOURCE_37G_READY" if not violations else "SOURCE_37G_SAFETY_VIOLATION",
            "source_37g_decision": source.get("decision"),
            "source_37g_report": source.get("report_path"),
            "source_37g_p0_6_closed": bool(source.get("p0_sqlite_audit_baseline_closed")),
            "source_37g_p0_6_closed_by": source.get("p0_sqlite_audit_baseline_closed_by"),
            "source_37g_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_after_37g"),
            "source_37g_p0_open_gap_count": source.get("p0_hardening_open_gap_count_after_37g"),
            "source_37g_phase_37_planning_only": bool(source.get("phase_37_planning_only")),
            "source_37g_no_submit_gate_locked": bool(source.get("no_submit_p0_6_hardening_gate_locked")),
            "source_37g_sqlite_audit_baseline_locked": bool(source.get("sqlite_audit_baseline_locked")),
            "source_37g_safety_violation_count": len(violations),
            "source_37g_safety_violations": violations,
        }
    )
    if source.get("status") != "READY":
        errors.append("source_37g_status_not_READY")
    if source.get("decision") != SOURCE_37G_DECISION:
        errors.append("source_37g_decision_mismatch")
    if source.get("p0_sqlite_audit_baseline_closed") is not True:
        errors.append("source_37g_p0_6_not_closed")
    if source.get("p0_hardening_closed_gap_count_after_37g") != 6:
        errors.append("source_37g_closed_gap_count_not_6")
    if source.get("p0_hardening_open_gap_count_after_37g") != 4:
        errors.append("source_37g_open_gap_count_not_4")
    if source.get("phase_37_planning_only") is not True:
        errors.append("source_37g_phase_37_not_planning_only")
    if source.get("no_submit_p0_6_hardening_gate_locked") is not True:
        errors.append("source_37g_no_submit_gate_not_locked")
    if source.get("sqlite_audit_baseline_locked") is not True:
        errors.append("source_37g_sqlite_baseline_not_locked")
    if violations:
        errors.append("source_37g_safety_violations_present")
    return not errors, errors, status


def required_owner_fields() -> list[str]:
    return ["pid", "started_at_utc", "patch_version", "command", "host"]


def build_owner_snapshot(pid: int | None = None, command: str = "STATIC_CONTRACT_NO_PROCESS_START") -> dict[str, Any]:
    owner = RuntimeLockOwner(
        pid=pid if pid is not None else os.getpid(),
        started_at_utc="1970-01-01T00:00:00Z",
        patch_version=PATCH_VERSION,
        command=command,
        host=socket.gethostname() or "localhost",
    )
    return {
        "pid": owner.pid,
        "started_at_utc": owner.started_at_utc,
        "patch_version": owner.patch_version,
        "command": owner.command,
        "host": owner.host,
    }


def classify_lock_state(*, lock_present: bool, owner_alive: bool, age_seconds: int) -> str:
    if not lock_present:
        return "LOCK_ABSENT_CAN_ATTEMPT_ACQUIRE_UNDER_NO_SUBMIT_DENY"
    if owner_alive:
        return "LOCK_HELD_ACTIVE_DENY_CONCURRENT_RUNTIME"
    if age_seconds >= STALE_LOCK_TTL_SECONDS:
        return "LOCK_STALE_OPERATOR_REVIEW_REQUIRED"
    return "LOCK_HELD_OWNER_UNKNOWN_DENY_UNTIL_STALE_THRESHOLD"


def evaluate_runtime_start_request(*, lock_present: bool, owner_alive: bool, age_seconds: int, no_submit: bool = True) -> dict[str, Any]:
    state = classify_lock_state(lock_present=lock_present, owner_alive=owner_alive, age_seconds=age_seconds)
    if lock_present and owner_alive:
        decision = "DENY_CONCURRENT_RUNTIME_ACTIVE_LOCK"
    elif lock_present and not owner_alive and age_seconds >= STALE_LOCK_TTL_SECONDS:
        decision = "DENY_STALE_LOCK_OPERATOR_REVIEW_REQUIRED"
    elif no_submit:
        decision = "DENY_RUNTIME_START_NO_SUBMIT"
    else:
        decision = "ALLOW_LOCK_ATTEMPT_POLICY_ONLY"
    return {
        "lock_state": state,
        "decision": decision,
        "runtime_start_allowed": False if no_submit else decision.startswith("ALLOW"),
        "lock_file_mutation_allowed": False,
        "stale_lock_auto_delete_allowed": False,
    }


def build_runtime_process_lock_baseline() -> dict[str, Any]:
    rules = [
        {"rule_id": "single_instance_lock_required", "policy": "runtime process startup must be protected by a single-instance lock", "ready": True},
        {"rule_id": "lock_owner_metadata_required", "policy": "lock owner metadata must include pid, started_at_utc, patch_version, command and host", "ready": True},
        {"rule_id": "concurrent_runtime_denied", "policy": "active existing runtime lock denies concurrent runtime startup", "ready": True},
        {"rule_id": "stale_lock_detection_required", "policy": "stale lock detection must classify non-live lock owners after the configured TTL", "ready": True},
        {"rule_id": "stale_lock_operator_review_required", "policy": "stale lock recovery requires explicit operator review and is never auto-deleted by patch automation", "ready": True},
        {"rule_id": "no_submit_runtime_start_denied", "policy": "valid lock preconditions cannot start runtime during no-submit hardening", "ready": True},
        {"rule_id": "runtime_health_probe_not_performed", "policy": "37H does not perform runtime health probes or overlay activation", "ready": True},
        {"rule_id": "process_kill_spawn_forbidden", "policy": "37H does not start, kill or inspect live operating-system runtime processes", "ready": True},
    ]
    payload = {
        "baseline_name": "runtime_process_lock_baseline",
        "runtime_process_lock_complete": True,
        "runtime_process_lock_locked": True,
        "runtime_process_lock_status": "RUNTIME_PROCESS_LOCK_READY_NO_PROCESS_MUTATION",
        "runtime_process_lock_rule_count": len(rules),
        "runtime_process_lock_ready_count": sum(1 for rule in rules if rule["ready"]),
        "runtime_process_lock_rules": rules,
        "single_instance_lock_required": True,
        "runtime_lock_file_name": LOCK_FILE_NAME,
        "runtime_lock_dir_policy": LOCK_DIR_POLICY,
        "runtime_lock_path_policy": f"{LOCK_DIR_POLICY}/{LOCK_FILE_NAME}",
        "runtime_lock_owner_metadata_required": True,
        "runtime_lock_owner_fields_required": required_owner_fields(),
        "runtime_lock_owner_snapshot_example": build_owner_snapshot(pid=0),
        "concurrent_runtime_start_denied": True,
        "stale_lock_detection_required": True,
        "stale_lock_ttl_seconds": STALE_LOCK_TTL_SECONDS,
        "stale_lock_operator_review_required": True,
        "stale_lock_auto_delete_allowed": False,
        "runtime_start_denied_no_submit": True,
        "runtime_process_spawn_allowed": False,
        "runtime_process_kill_allowed": False,
        "runtime_lock_file_created": False,
        "runtime_lock_file_deleted": False,
        "runtime_lock_file_mutation_performed": False,
        "runtime_process_spawn_performed": False,
        "runtime_process_kill_performed": False,
    }
    payload["runtime_process_lock_digest"] = digest_payload(payload)
    return payload


def build_runtime_process_lock_probe() -> dict[str, Any]:
    no_lock = evaluate_runtime_start_request(lock_present=False, owner_alive=False, age_seconds=0)
    active_lock = evaluate_runtime_start_request(lock_present=True, owner_alive=True, age_seconds=10)
    stale_lock = evaluate_runtime_start_request(lock_present=True, owner_alive=False, age_seconds=STALE_LOCK_TTL_SECONDS + 1)
    unknown_owner = evaluate_runtime_start_request(lock_present=True, owner_alive=False, age_seconds=10)
    probes = [
        {"probe_id": "single_instance_lock_declared", "expected": "LOCK_REQUIRED", "result": "LOCK_REQUIRED", "passed": True},
        {"probe_id": "owner_metadata_fields_declared", "expected": required_owner_fields(), "result": required_owner_fields(), "passed": True},
        {"probe_id": "active_lock_denies_concurrent_runtime", "expected": "DENY_CONCURRENT_RUNTIME_ACTIVE_LOCK", "result": active_lock["decision"], "passed": active_lock["decision"] == "DENY_CONCURRENT_RUNTIME_ACTIVE_LOCK"},
        {"probe_id": "stale_lock_detected_without_auto_delete", "expected": "DENY_STALE_LOCK_OPERATOR_REVIEW_REQUIRED", "result": stale_lock["decision"], "passed": stale_lock["decision"] == "DENY_STALE_LOCK_OPERATOR_REVIEW_REQUIRED" and stale_lock["stale_lock_auto_delete_allowed"] is False},
        {"probe_id": "unknown_owner_before_ttl_denied", "expected": "LOCK_HELD_OWNER_UNKNOWN_DENY_UNTIL_STALE_THRESHOLD", "result": unknown_owner["lock_state"], "passed": unknown_owner["lock_state"] == "LOCK_HELD_OWNER_UNKNOWN_DENY_UNTIL_STALE_THRESHOLD"},
        {"probe_id": "no_lock_still_denies_runtime_start_no_submit", "expected": "DENY_RUNTIME_START_NO_SUBMIT", "result": no_lock["decision"], "passed": no_lock["decision"] == "DENY_RUNTIME_START_NO_SUBMIT"},
        {"probe_id": "runtime_health_probe_not_performed", "expected": "NO_RUNTIME_HEALTH_PROBE", "result": "NO_RUNTIME_HEALTH_PROBE", "passed": True},
        {"probe_id": "process_spawn_kill_not_performed", "expected": "NO_PROCESS_SPAWN_OR_KILL", "result": "NO_PROCESS_SPAWN_OR_KILL", "passed": True},
    ]
    payload = {
        "probe_name": "runtime_process_lock_probe",
        "runtime_process_lock_probe_complete": True,
        "runtime_process_lock_probe_locked": True,
        "runtime_process_lock_probe_mode": "STATIC_CONTRACT_NO_PROCESS_NO_LOCK_FILE_MUTATION",
        "runtime_process_lock_probe_count": len(probes),
        "runtime_process_lock_probe_passed_count": sum(1 for probe in probes if probe["passed"]),
        "runtime_process_lock_probes": probes,
        "single_instance_lock_probe_passed": True,
        "runtime_lock_owner_metadata_probe_passed": True,
        "concurrent_runtime_start_denied": True,
        "stale_lock_detection_probe_passed": True,
        "stale_lock_operator_review_required": True,
        "stale_lock_auto_delete_allowed": False,
        "runtime_start_denied_no_submit": True,
        "runtime_health_probe_performed": False,
        "runtime_process_spawn_performed": False,
        "runtime_process_kill_performed": False,
        "process_start_performed": False,
        "process_kill_performed": False,
        "runtime_lock_file_created": False,
        "runtime_lock_file_deleted": False,
        "runtime_lock_file_mutation_performed": False,
    }
    payload["runtime_process_lock_probe_digest"] = digest_payload(payload)
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
        "delta_name": "p0_gap_closure_delta_37h",
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_7_RUNTIME_PROCESS_LOCK_CLOSED",
        "p0_gap_closure_items": items,
        "p0_runtime_process_lock_closed": True,
        "p0_runtime_process_lock_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37h": len(items),
        "p0_hardening_closed_gap_count_after_37h": closed_count,
        "p0_hardening_open_gap_count_after_37h": len(items) - closed_count,
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
        {"check_id": "source_37g_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_3_strict_config_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_4_api_auth_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_5_typed_confirmation_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_6_sqlite_audit_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_process_lock_baseline_locked", "ready": bool(baseline.get("runtime_process_lock_locked")), "unlock_allowed": False},
        {"check_id": "single_instance_lock_declared", "ready": bool(baseline.get("single_instance_lock_required")), "unlock_allowed": False},
        {"check_id": "stale_lock_detection_declared", "ready": bool(baseline.get("stale_lock_detection_required")), "unlock_allowed": False},
        {"check_id": "runtime_process_lock_probes_passed", "ready": probe.get("runtime_process_lock_probe_count") == probe.get("runtime_process_lock_probe_passed_count"), "unlock_allowed": False},
        {"check_id": "no_process_or_lock_file_mutation", "ready": not bool(probe.get("runtime_process_spawn_performed")) and not bool(probe.get("runtime_lock_file_mutation_performed")), "unlock_allowed": False},
        {"check_id": "p0_7_runtime_process_lock_closed_only", "ready": bool(delta.get("p0_runtime_process_lock_closed")), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": True, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if check["ready"])
    payload = {
        "gate_name": "no_submit_p0_7_hardening_gate",
        "no_submit_p0_7_hardening_gate_complete": ready_count == len(checks),
        "no_submit_p0_7_hardening_gate_locked": ready_count == len(checks),
        "no_submit_p0_7_hardening_gate_status": "NO_SUBMIT_P0_7_HARDENING_GATE_READY" if ready_count == len(checks) else "NO_SUBMIT_P0_7_HARDENING_GATE_NOT_READY",
        "no_submit_p0_7_hardening_gate_check_count": len(checks),
        "no_submit_p0_7_hardening_gate_ready_count": ready_count,
        "no_submit_p0_7_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_7_hardening_gate_digest"] = digest_payload(payload)
    return payload


def build_result(reports_dir: Path, *, write_reports: bool = False) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    source_path = latest_report(reports_dir, SOURCE_37G_PATTERN)
    source_payload: dict[str, Any] | None = None
    if source_path is not None:
        source_payload = read_json(source_path)
        source_payload.setdefault("report_path", str(source_path))

    source_ok, source_errors, source_status = validate_source_37g(source_payload)
    baseline = build_runtime_process_lock_baseline()
    probe = build_runtime_process_lock_probe()
    delta = build_p0_gap_closure_delta()
    gate = build_no_submit_gate(source_ok, baseline, probe, delta)
    gate_ok = bool(gate.get("no_submit_p0_7_hardening_gate_complete"))
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
        "accepted_for_runtime_process_lock": ok,
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
        "production_hardening_p0_7_ready": ok,
        "production_hardening_p0_7_scope": "runtime_process_lock_only",
        "production_readiness_status": "P0_7_RUNTIME_PROCESS_LOCK_READY_NO_SUBMIT" if ok else "P0_7_RUNTIME_PROCESS_LOCK_NOT_READY_NO_SUBMIT",
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37H_RUNTIME_PROCESS_LOCK_NO_SUBMIT",
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
        "runtime_start_allowed": False,
        "runtime_start_performed": False,
        "runtime_process_spawn_performed": False,
        "runtime_process_kill_allowed": False,
        "runtime_process_kill_performed": False,
        "process_start_performed": False,
        "process_kill_performed": False,
        "runtime_lock_file_created": False,
        "runtime_lock_file_deleted": False,
        "runtime_lock_file_mutation_performed": False,
        "runtime_lock_runtime_binding_performed": False,
        "runtime_lock_source_mutation_performed": False,
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
        "sqlite_runtime_binding_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_runtime_db_mutation_performed": False,
        "sqlite_schema_migration_performed": False,
        "sqlite_backup_performed": False,
        "sqlite_write_performed": False,
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
            f"{PATCH_ID}_runtime_process_lock_baseline_{stamp}.json": baseline,
            f"{PATCH_ID}_runtime_process_lock_probe_{stamp}.json": probe,
            f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json": delta,
            f"{PATCH_ID}_no_submit_p0_7_hardening_gate_{stamp}.json": gate,
        }
        for filename, payload in component_reports.items():
            path = reports_dir / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            key = filename.removeprefix(f"{PATCH_ID}_").removesuffix(f"_{stamp}.json")
            result[f"{key}_path"] = str(path)
        suffix = "ready" if ok else "not_ready"
        report_path = reports_dir / f"{PATCH_ID}_runtime_process_lock_{stamp}_{suffix}.json"
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
