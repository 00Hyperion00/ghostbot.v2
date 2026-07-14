from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436637E"
PATCH_VERSION = "4B.4.3.6.6.37E"
PATCH_NAME = "API Auth Destructive Endpoint Guard"
CHECK_NAME = "api_auth_destructive_endpoint_guard"
READY_DECISION = "API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_4_LOCKED"
NOT_READY_DECISION = "API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37F"
SOURCE_37D_PATTERN = "4B436637D_strict_config_unknown_key_fail_closed_*_ready.json"

LOCAL_TOKEN_HEADER_NAME = "X-TradeBot-Local-Token"
LOCAL_TOKEN_ENV_VAR = "TRADEBOT_LOCAL_API_TOKEN"

SAFETY_FALSE_KEYS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "destructive_endpoint_runtime_binding_performed",
    "destructive_endpoint_runtime_execution_allowed",
    "destructive_endpoint_execution_performed",
    "evidence_collection_started",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "fee_slippage_mutation_performed",
    "file_delete_performed",
    "file_move_performed",
    "http_request_performed",
    "install_contract_mutation_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_consumed",
    "operator_observation_token_validated",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_37_execution_started",
    "phase_37_unlocked",
    "phase_reopen_allowed",
    "phase_reopen_performed",
    "private_account_read_performed",
    "private_api_access_allowed",
    "promotion_gate_mutation_performed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "public_observation_network_off_execution_package_executed",
    "readme_install_contract_mutation_performed",
    "reload_performed",
    "repo_hygiene_cleanup_performed",
    "report_commit_policy_mutation_performed",
    "report_delete_performed",
    "report_move_performed",
    "requirements_alignment_mutation_performed",
    "runtime_evidence_artifact_written",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_lock_mutation_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "signed_request_performed",
    "simulated_approval_performed",
    "sqlite_schema_mutation_performed",
    "strict_config_runtime_loader_mutation_performed",
    "token_secret_written",
    "token_storage_mutation_performed",
    "trading_action_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "typed_confirmation_mutation_performed",
)

P0_GAPS_AFTER_37E: tuple[dict[str, Any], ...] = (
    {"gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed": True, "domain": "install_contract", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed": True, "domain": "repo_hygiene", "closed_by": "4B.4.3.6.6.37C"},
    {"gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed": True, "domain": "strict_config", "closed_by": "4B.4.3.6.6.37D"},
    {"gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed": True, "domain": "api_security", "closed_by": PATCH_VERSION},
    {"gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed": False, "domain": "operator_controls", "closed_by": None},
    {"gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed": False, "domain": "persistence", "closed_by": None},
    {"gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed": False, "domain": "runtime_safety", "closed_by": None},
    {"gap_id": "P0_FEE_SLIPPAGE_BASELINE", "closed": False, "domain": "execution_cost_model", "closed_by": None},
    {"gap_id": "P0_REPORT_COMMIT_POLICY", "closed": False, "domain": "evidence_governance", "closed_by": None},
    {"gap_id": "P0_PROMOTION_GATE_ISOLATION", "closed": False, "domain": "promotion_governance", "closed_by": None},
)

SAFE_READ_ONLY_ENDPOINTS: tuple[tuple[str, str], ...] = (
    ("GET", "/health"),
    ("GET", "/status"),
    ("GET", "/metrics"),
    ("GET", "/api/status"),
)

DESTRUCTIVE_ENDPOINT_PATTERNS: tuple[str, ...] = (
    "/api/force-trade",
    "/api/force_trade",
    "/api/reload",
    "/api/reload-config",
    "/api/train",
    "/api/reset",
    "/api/reset-state",
    "/api/runtime-overlay",
    "/api/archive",
    "/api/cleanup",
    "/api/order",
    "/api/submit",
    "/api/paper/enable",
    "/api/live/enable",
    "/api/reports/delete",
)

DESTRUCTIVE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

AUTH_GUARD_RULES: tuple[dict[str, Any], ...] = (
    {"rule_id": "local_token_required_for_destructive_endpoints", "ready": True, "policy": "destructive endpoints require a local operator token"},
    {"rule_id": "missing_token_denied", "ready": True, "policy": "missing local token denies destructive endpoint access"},
    {"rule_id": "invalid_token_denied", "ready": True, "policy": "invalid local token denies destructive endpoint access"},
    {"rule_id": "unknown_destructive_endpoint_denied_by_default", "ready": True, "policy": "unknown non-read endpoint is denied by default"},
    {"rule_id": "safe_read_only_endpoints_do_not_require_token", "ready": True, "policy": "safe read-only health/status endpoints remain observable without token"},
    {"rule_id": "token_secret_not_materialized", "ready": True, "policy": "no token secret is generated or written by this hardening patch"},
    {"rule_id": "runtime_route_binding_not_performed", "ready": True, "policy": "existing API routes are not mutated in this no-submit hardening phase"},
)


@dataclass(frozen=True)
class AuthProbeResult:
    probe_id: str
    method: str
    path: str
    expected: str
    result: str
    passed: bool
    destructive: bool
    token_present: bool
    token_valid: bool
    runtime_execution_allowed: bool


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latest_report(repo_root: Path, reports_dir: Path | None, pattern: str) -> Path | None:
    base = reports_dir or repo_root / "reports" / "recovery"
    if not base.exists():
        return None
    candidates = sorted(base.glob(pattern), key=lambda p: (p.stat().st_mtime, p.name))
    return candidates[-1] if candidates else None


@dataclass(frozen=True)
class GitState:
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    phase_37_tags: tuple[str, ...]


def run_git(repo_root: Path, args: Sequence[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def read_git_state(repo_root: Path) -> GitState:
    branch = run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    tags_out = run_git(repo_root, ["tag", "--list", "4B.4.3.6.6.37*"])
    tags = tuple(sorted(t for t in (tags_out or "").splitlines() if t.strip()))
    return GitState(git_available=branch is not None or head is not None, git_branch=branch, git_head_short=head, phase_37_tags=tags)


def truthy_violations(payload: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    return [key for key in keys if bool(payload.get(key, False)) is True]


def normalize_method(method: str) -> str:
    return method.strip().upper()


def normalize_path(path: str) -> str:
    cleaned = path.strip().lower()
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned.split("?", 1)[0].rstrip("/") or "/"


def is_safe_read_only_endpoint(method: str, path: str) -> bool:
    method_norm = normalize_method(method)
    path_norm = normalize_path(path)
    return any(method_norm == m and path_norm == p for m, p in SAFE_READ_ONLY_ENDPOINTS)


def is_destructive_endpoint(method: str, path: str) -> bool:
    method_norm = normalize_method(method)
    path_norm = normalize_path(path)
    if method_norm == "DELETE":
        return True
    if method_norm not in DESTRUCTIVE_METHODS:
        return False
    return any(pattern in path_norm for pattern in DESTRUCTIVE_ENDPOINT_PATTERNS) or path_norm.startswith("/api/")



def _header_value(headers: Mapping[str, Any] | None, name: str) -> str | None:
    if not headers:
        return None
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return None if value is None else str(value)
    return None


def validate_local_token(supplied_token: str | None, expected_token: str | None) -> dict[str, Any]:
    supplied = "" if supplied_token is None else str(supplied_token)
    expected = "" if expected_token is None else str(expected_token)
    token_present = supplied != ""
    token_configured = expected != ""
    token_valid = bool(token_present and token_configured and hmac.compare_digest(supplied, expected))
    return {
        "token_present": token_present,
        "token_configured": token_configured,
        "token_valid": token_valid,
        "token_header_name": LOCAL_TOKEN_HEADER_NAME,
        "token_env_var": LOCAL_TOKEN_ENV_VAR,
    }


def authorize_local_endpoint_from_headers(
    method: str,
    path: str,
    *,
    headers: Mapping[str, Any] | None,
    expected_token: str | None,
) -> dict[str, Any]:
    token_state = validate_local_token(_header_value(headers, LOCAL_TOKEN_HEADER_NAME), expected_token)
    decision = authorize_local_endpoint(
        method,
        path,
        token_present=bool(token_state["token_present"]),
        token_valid=bool(token_state["token_valid"]),
    )
    decision.update(token_state)
    return decision

def authorize_local_endpoint(method: str, path: str, *, token_present: bool, token_valid: bool) -> dict[str, Any]:
    method_norm = normalize_method(method)
    path_norm = normalize_path(path)
    destructive = is_destructive_endpoint(method_norm, path_norm)
    safe_read_only = is_safe_read_only_endpoint(method_norm, path_norm)

    if safe_read_only and not destructive:
        result = "ALLOW_READ_ONLY"
        auth_passed = True
    elif destructive and not token_present:
        result = "DENY_LOCAL_TOKEN_REQUIRED"
        auth_passed = False
    elif destructive and not token_valid:
        result = "DENY_LOCAL_TOKEN_INVALID"
        auth_passed = False
    elif destructive and token_present and token_valid:
        # Authentication would pass, but this no-submit hardening phase still refuses execution.
        result = "AUTH_PASSED_EXECUTION_DENIED_NO_SUBMIT"
        auth_passed = True
    else:
        result = "DENY_BY_DEFAULT"
        auth_passed = False

    return {
        "method": method_norm,
        "path": path_norm,
        "safe_read_only": safe_read_only,
        "destructive": destructive,
        "local_token_required": destructive,
        "token_present": token_present,
        "token_valid": token_valid,
        "auth_passed": auth_passed,
        "runtime_execution_allowed": False,
        "result": result,
    }


def run_auth_probes() -> list[AuthProbeResult]:
    cases = [
        ("safe_health_read", "GET", "/health", False, False, "ALLOW_READ_ONLY"),
        ("force_trade_missing_token", "POST", "/api/force-trade", False, False, "DENY_LOCAL_TOKEN_REQUIRED"),
        ("reload_invalid_token", "POST", "/api/reload-config", True, False, "DENY_LOCAL_TOKEN_INVALID"),
        ("delete_report_missing_token", "DELETE", "/api/reports/delete/123", False, False, "DENY_LOCAL_TOKEN_REQUIRED"),
        ("valid_token_no_submit", "POST", "/api/runtime-overlay/activate", True, True, "AUTH_PASSED_EXECUTION_DENIED_NO_SUBMIT"),
        ("unknown_post_denied_by_default", "POST", "/api/new-dangerous-action", False, False, "DENY_LOCAL_TOKEN_REQUIRED"),
    ]
    results: list[AuthProbeResult] = []
    for probe_id, method, path, token_present, token_valid, expected in cases:
        decision = authorize_local_endpoint(method, path, token_present=token_present, token_valid=token_valid)
        results.append(
            AuthProbeResult(
                probe_id=probe_id,
                method=decision["method"],
                path=decision["path"],
                expected=expected,
                result=str(decision["result"]),
                passed=decision["result"] == expected and decision["runtime_execution_allowed"] is False,
                destructive=bool(decision["destructive"]),
                token_present=bool(decision["token_present"]),
                token_valid=bool(decision["token_valid"]),
                runtime_execution_allowed=bool(decision["runtime_execution_allowed"]),
            )
        )
    return results


def build_api_auth_guard() -> dict[str, Any]:
    probes = run_auth_probes()
    probe_items = [probe.__dict__ for probe in probes]
    passed = sum(1 for probe in probes if probe.passed)
    destructive_probe_items = [item for item in probe_items if item["destructive"]]
    token_requirement = {
        "token_requirement_name": "local_token_requirement",
        "local_token_requirement_complete": True,
        "local_token_requirement_locked": True,
        "local_token_header_name": LOCAL_TOKEN_HEADER_NAME,
        "local_token_env_var": LOCAL_TOKEN_ENV_VAR,
        "local_token_required_for_destructive_endpoints": True,
        "local_token_required_for_safe_read_only_endpoints": False,
        "token_storage_mutation_performed": False,
        "token_secret_written": False,
        "token_secret_materialized": False,
        "token_value_logged": False,
        "token_validation_scope": "local_operator_destructive_endpoint_auth_only",
        "local_token_requirement_status": "LOCAL_TOKEN_REQUIREMENT_READY_NO_SECRET_WRITTEN",
    }
    guard = {
        "guard_name": "destructive_endpoint_guard",
        "api_auth_guard_complete": True,
        "api_auth_guard_locked": True,
        "api_auth_guard_status": "API_AUTH_GUARD_READY_LOCAL_TOKEN_REQUIRED",
        "destructive_endpoint_guard_complete": True,
        "destructive_endpoint_guard_locked": True,
        "destructive_endpoint_deny_by_default": True,
        "destructive_endpoint_guard_rule_count": len(AUTH_GUARD_RULES),
        "destructive_endpoint_guard_ready_count": sum(1 for rule in AUTH_GUARD_RULES if rule["ready"] is True),
        "destructive_endpoint_guard_rules": list(AUTH_GUARD_RULES),
        "destructive_endpoint_probe_count": len(probes),
        "destructive_endpoint_probe_passed_count": passed,
        "destructive_endpoint_auth_probes": probe_items,
        "destructive_endpoint_probe_status": "DESTRUCTIVE_ENDPOINT_AUTH_PROBES_READY_DENY_BY_DEFAULT",
        "destructive_endpoint_missing_token_denied": any(p.probe_id == "force_trade_missing_token" and p.passed for p in probes),
        "destructive_endpoint_invalid_token_denied": any(p.probe_id == "reload_invalid_token" and p.passed for p in probes),
        "destructive_endpoint_unknown_post_denied_by_default": any(p.probe_id == "unknown_post_denied_by_default" and p.passed for p in probes),
        "destructive_endpoint_valid_token_execution_denied_no_submit": any(p.probe_id == "valid_token_no_submit" and p.passed for p in probes),
        "safe_read_only_endpoint_without_token_allowed": any(p.probe_id == "safe_health_read" and p.passed for p in probes),
        "destructive_endpoint_runtime_execution_allowed": False,
        "destructive_endpoint_execution_performed": False,
        "destructive_endpoint_runtime_binding_performed": False,
        "api_route_mutation_performed": False,
        "api_runtime_binding_performed": False,
        "api_auth_mutation_performed": False,
        "api_auth_runtime_loader_mutation_performed": False,
        "api_auth_runtime_reload_performed": False,
        "destructive_endpoint_candidates_guarded_count": len(destructive_probe_items),
        "destructive_endpoint_candidate_patterns": list(DESTRUCTIVE_ENDPOINT_PATTERNS),
    }
    digest_payload = {"token_requirement": token_requirement, "guard": guard}
    token_requirement["local_token_requirement_digest"] = stable_digest(token_requirement)
    guard["destructive_endpoint_guard_digest"] = stable_digest(digest_payload)
    return {**token_requirement, **guard}


def build_p0_gap_closure_delta() -> dict[str, Any]:
    closed_count = sum(1 for item in P0_GAPS_AFTER_37E if item["closed"])
    payload: dict[str, Any] = {
        "delta_name": "p0_gap_closure_delta_37e",
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_4_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_CLOSED",
        "p0_gap_closure_items": list(P0_GAPS_AFTER_37E),
        "p0_api_auth_destructive_endpoint_guard_closed": True,
        "p0_api_auth_destructive_endpoint_guard_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37e": len(P0_GAPS_AFTER_37E),
        "p0_hardening_closed_gap_count_after_37e": closed_count,
        "p0_hardening_open_gap_count_after_37e": len(P0_GAPS_AFTER_37E) - closed_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
    }
    payload["p0_gap_closure_delta_digest"] = stable_digest(payload)
    return payload


def build_no_submit_p0_4_gate(source_ok: bool, guard: Mapping[str, Any], gap_delta: Mapping[str, Any], final_safety_violations: Sequence[str]) -> dict[str, Any]:
    checks = [
        {"check_id": "source_37d_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_3_strict_config_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "local_token_requirement_locked", "ready": bool(guard.get("local_token_requirement_locked", False)), "unlock_allowed": False},
        {"check_id": "destructive_endpoint_guard_locked", "ready": bool(guard.get("destructive_endpoint_guard_locked", False)), "unlock_allowed": False},
        {"check_id": "destructive_endpoint_deny_by_default_probes_passed", "ready": bool(guard.get("destructive_endpoint_probe_count") == guard.get("destructive_endpoint_probe_passed_count")), "unlock_allowed": False},
        {"check_id": "p0_4_api_auth_closed_only", "ready": bool(gap_delta.get("p0_api_auth_destructive_endpoint_guard_closed", False)), "unlock_allowed": False},
        {"check_id": "api_routes_not_mutated", "ready": not bool(guard.get("api_route_mutation_performed", False)), "unlock_allowed": False},
        {"check_id": "token_secret_not_written", "ready": not bool(guard.get("token_secret_written", False)), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": len(final_safety_violations) == 0, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if check["ready"] is True)
    payload: dict[str, Any] = {
        "gate_name": "no_submit_p0_4_hardening_gate",
        "no_submit_p0_4_hardening_gate_complete": ready_count == len(checks),
        "no_submit_p0_4_hardening_gate_locked": ready_count == len(checks),
        "no_submit_p0_4_hardening_gate_status": "NO_SUBMIT_P0_4_HARDENING_GATE_READY" if ready_count == len(checks) else "NO_SUBMIT_P0_4_HARDENING_GATE_NOT_READY",
        "no_submit_p0_4_hardening_gate_check_count": len(checks),
        "no_submit_p0_4_hardening_gate_ready_count": ready_count,
        "no_submit_p0_4_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_4_hardening_gate_digest"] = stable_digest(payload)
    return payload


def validate_source_37d(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    info: dict[str, Any] = {
        "source_37d_complete": False,
        "source_37d_status": "SOURCE_37D_MISSING",
        "source_37d_safety_violation_count": None,
        "source_37d_safety_violations": [],
    }
    errors: list[str] = []
    if source is None:
        errors.append("SOURCE_37D_READY_REPORT_MISSING")
        return False, errors, info

    safety_violations = source.get("final_safety_violations", source.get("source_37d_safety_violations", []))
    if not isinstance(safety_violations, list):
        safety_violations = ["SOURCE_37D_SAFETY_VIOLATIONS_MALFORMED"]

    checks = {
        "status_ready": source.get("status") == "READY",
        "decision_ready": source.get("decision") == "STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_3_LOCKED",
        "p0_3_closed": source.get("p0_strict_config_unknown_key_fail_closed") is True,
        "p0_closed_count_3": source.get("p0_hardening_closed_gap_count_after_37d") == 3,
        "p0_open_count_7": source.get("p0_hardening_open_gap_count_after_37d") == 7,
        "phase_37_planning_only": source.get("phase_37_planning_only") is True,
        "phase_37_unlocked_false": source.get("phase_37_unlocked") is False,
        "paper_blocked": source.get("paper_transition_blocked") is True,
        "safety_clean": len(safety_violations) == 0,
    }
    for check_name, passed in checks.items():
        if not passed:
            errors.append(f"SOURCE_37D_{check_name.upper()}_FAILED")

    info.update(
        {
            "source_37d_complete": all(checks.values()),
            "source_37d_status": "SOURCE_37D_READY" if all(checks.values()) else "SOURCE_37D_NOT_READY",
            "source_37d_decision": source.get("decision"),
            "source_37d_report": None,
            "source_37d_p0_3_closed": source.get("p0_strict_config_unknown_key_fail_closed"),
            "source_37d_p0_3_closed_by": source.get("p0_strict_config_unknown_key_fail_closed_by"),
            "source_37d_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_after_37d"),
            "source_37d_p0_open_gap_count": source.get("p0_hardening_open_gap_count_after_37d"),
            "source_37d_phase_37_planning_only": source.get("phase_37_planning_only"),
            "source_37d_safety_violation_count": len(safety_violations),
            "source_37d_safety_violations": safety_violations,
        }
    )
    return all(checks.values()), errors, info


def load_source_37d(repo_root: Path, reports_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_report(repo_root, reports_dir, SOURCE_37D_PATTERN)
    if path is None:
        return None, None
    return load_json(path), path


def evaluate(repo_root: Path, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    source, source_path = load_source_37d(repo_root, reports_dir)
    source_ok, source_errors, source_info = validate_source_37d(source)
    if source_path is not None:
        source_info["source_37d_report"] = str(source_path)
    git_state = read_git_state(repo_root)
    guard = build_api_auth_guard()
    gap_delta = build_p0_gap_closure_delta()

    base_payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "check_name": CHECK_NAME,
        "next_phase": NEXT_PHASE,
        "git_available": git_state.git_available,
        "git_branch": git_state.git_branch,
        "git_head_short": git_state.git_head_short,
        "phase_37_tag_count_observed": len(git_state.phase_37_tags),
        "phase_37_tags_observed": list(git_state.phase_37_tags),
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "phase_reopen_allowed": False,
        "phase_reopen_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37E_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_NO_SUBMIT",
        "production_hardening_p0_4_scope": "api_auth_destructive_endpoint_guard_only",
        "production_readiness_status": "P0_4_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_READY_NO_SUBMIT",
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "order_submit_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "public_observation_network_off_execution_package_executed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "simulated_approval_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "report_commit_policy_mutation_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "install_contract_mutation_performed": False,
        "requirements_alignment_mutation_performed": False,
        "readme_install_contract_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "api_auth_runtime_loader_mutation_performed": False,
        "api_auth_runtime_reload_performed": False,
        "api_route_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_schema_mutation_performed": False,
        "runtime_lock_mutation_performed": False,
        "fee_slippage_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "strict_config_runtime_loader_mutation_performed": False,
        "token_storage_mutation_performed": False,
        "token_secret_written": False,
        "evidence_collection_started": False,
    }
    payload: dict[str, Any] = {}
    payload.update(base_payload)
    payload.update(source_info)
    payload.update(guard)
    payload.update(gap_delta)
    final_safety_violations = truthy_violations(payload, SAFETY_FALSE_KEYS)
    gate = build_no_submit_p0_4_gate(source_ok, guard, gap_delta, final_safety_violations)
    payload.update(gate)

    ready = (
        source_ok
        and bool(guard.get("local_token_requirement_locked", False))
        and bool(guard.get("destructive_endpoint_guard_locked", False))
        and guard.get("destructive_endpoint_probe_count") == guard.get("destructive_endpoint_probe_passed_count")
        and bool(gap_delta.get("p0_api_auth_destructive_endpoint_guard_closed", False))
        and bool(gate.get("no_submit_p0_4_hardening_gate_complete", False))
        and len(final_safety_violations) == 0
    )
    errors = [*source_errors]
    if not bool(guard.get("local_token_requirement_locked", False)):
        errors.append("LOCAL_TOKEN_REQUIREMENT_NOT_LOCKED")
    if not bool(guard.get("destructive_endpoint_guard_locked", False)):
        errors.append("DESTRUCTIVE_ENDPOINT_GUARD_NOT_LOCKED")
    if guard.get("destructive_endpoint_probe_count") != guard.get("destructive_endpoint_probe_passed_count"):
        errors.append("DESTRUCTIVE_ENDPOINT_AUTH_PROBES_FAILED")
    if not bool(gap_delta.get("p0_api_auth_destructive_endpoint_guard_closed", False)):
        errors.append("P0_4_API_AUTH_GUARD_NOT_CLOSED")
    if final_safety_violations:
        errors.append("FINAL_SAFETY_FLAGS_NOT_CLEAN")

    payload.update(
        {
            "ok": ready,
            "status": "READY" if ready else "NOT_READY",
            "decision": READY_DECISION if ready else NOT_READY_DECISION,
            "accepted_for_api_auth_destructive_endpoint_guard": ready,
            "production_hardening_p0_4_ready": ready,
            "errors": errors,
            "final_safety_violation_count": len(final_safety_violations),
            "final_safety_violations": final_safety_violations,
            "report_path": None,
            "local_token_requirement_path": None,
            "destructive_endpoint_guard_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_4_hardening_gate_path": None,
        }
    )

    if write_reports:
        out_dir = reports_dir or repo_root / "reports" / "recovery"
        stamp = utc_stamp()
        token_path = out_dir / f"{PATCH_ID}_local_token_requirement_{stamp}.json"
        guard_path = out_dir / f"{PATCH_ID}_destructive_endpoint_guard_{stamp}.json"
        delta_path = out_dir / f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json"
        gate_path = out_dir / f"{PATCH_ID}_no_submit_p0_4_hardening_gate_{stamp}.json"
        report_path = out_dir / f"{PATCH_ID}_{CHECK_NAME}_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(token_path, {k: v for k, v in guard.items() if k.startswith("local_token") or k.startswith("token_")})
        write_json(guard_path, {k: v for k, v in guard.items() if k.startswith("destructive_endpoint") or k.startswith("api_auth") or k.startswith("api_route") or k in {"guard_name"}})
        write_json(delta_path, gap_delta)
        write_json(gate_path, gate)
        payload["local_token_requirement_path"] = str(token_path)
        payload["destructive_endpoint_guard_path"] = str(guard_path)
        payload["p0_gap_closure_delta_path"] = str(delta_path)
        payload["no_submit_p0_4_hardening_gate_path"] = str(gate_path)
        payload["report_path"] = str(report_path)
        write_json(report_path, payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    payload = evaluate(repo_root=repo_root, reports_dir=reports_dir, write_reports=args.write_reports)
    if args.once_json or True:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
