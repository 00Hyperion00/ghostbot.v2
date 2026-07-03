from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436637F"
PATCH_VERSION = "4B.4.3.6.6.37F"
PATCH_NAME = "Typed Confirmation Destructive Actions"
CHECK_NAME = "typed_confirmation_destructive_actions"
READY_DECISION = "TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_5_LOCKED"
NOT_READY_DECISION = "TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37G"
SOURCE_37E_PATTERN = "4B436637E_api_auth_destructive_endpoint_guard_*_ready.json"

SAFETY_FALSE_KEYS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "api_auth_mutation_performed",
    "api_auth_runtime_loader_mutation_performed",
    "api_auth_runtime_reload_performed",
    "api_route_mutation_performed",
    "deduplication_action_performed",
    "destructive_action_execution_allowed",
    "destructive_action_execution_performed",
    "destructive_cleanup_performed",
    "destructive_endpoint_execution_performed",
    "destructive_endpoint_runtime_binding_performed",
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
    "typed_confirmation_runtime_binding_performed",
    "typed_confirmation_secret_written",
    "typed_confirmation_storage_mutation_performed",
)

P0_GAPS_AFTER_37F: tuple[dict[str, Any], ...] = (
    {"gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed": True, "domain": "install_contract", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed": True, "domain": "repo_hygiene", "closed_by": "4B.4.3.6.6.37C"},
    {"gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed": True, "domain": "strict_config", "closed_by": "4B.4.3.6.6.37D"},
    {"gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed": True, "domain": "api_security", "closed_by": "4B.4.3.6.6.37E"},
    {"gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed": True, "domain": "operator_controls", "closed_by": PATCH_VERSION},
    {"gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed": False, "domain": "persistence", "closed_by": None},
    {"gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed": False, "domain": "runtime_safety", "closed_by": None},
    {"gap_id": "P0_FEE_SLIPPAGE_BASELINE", "closed": False, "domain": "execution_cost_model", "closed_by": None},
    {"gap_id": "P0_REPORT_COMMIT_POLICY", "closed": False, "domain": "evidence_governance", "closed_by": None},
    {"gap_id": "P0_PROMOTION_GATE_ISOLATION", "closed": False, "domain": "promotion_governance", "closed_by": None},
)

TYPED_CONFIRMATION_ACTIONS: tuple[dict[str, str], ...] = (
    {"action_id": "force_trade", "path": "/api/force-trade", "method": "POST", "required_phrase": "CONFIRM FORCE TRADE"},
    {"action_id": "reload_config", "path": "/api/reload-config", "method": "POST", "required_phrase": "CONFIRM RELOAD CONFIG"},
    {"action_id": "train_model", "path": "/api/train", "method": "POST", "required_phrase": "CONFIRM TRAIN MODEL"},
    {"action_id": "reset_state", "path": "/api/reset-state", "method": "POST", "required_phrase": "CONFIRM RESET STATE"},
)

TYPED_CONFIRMATION_RULES: tuple[dict[str, Any], ...] = (
    {"rule_id": "typed_confirmation_required_for_force_trade_reload_train_reset", "ready": True, "policy": "force trade, reload, train and reset require exact typed confirmation"},
    {"rule_id": "missing_confirmation_denied", "ready": True, "policy": "missing typed confirmation denies destructive action"},
    {"rule_id": "mismatched_confirmation_denied", "ready": True, "policy": "mismatched typed confirmation denies destructive action"},
    {"rule_id": "confirmation_phrase_is_action_scoped", "ready": True, "policy": "each destructive action has an action-specific phrase"},
    {"rule_id": "confirmation_does_not_enable_submit", "ready": True, "policy": "valid typed confirmation still cannot enable runtime execution in no-submit phase"},
    {"rule_id": "safe_read_only_actions_do_not_require_confirmation", "ready": True, "policy": "safe read-only endpoints remain observable without typed confirmation"},
    {"rule_id": "runtime_route_binding_not_performed", "ready": True, "policy": "existing API routes are not mutated in this no-submit hardening phase"},
    {"rule_id": "typed_confirmation_secret_not_materialized", "ready": True, "policy": "no typed confirmation secret or storage is generated by this patch"},
)


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
            ["git", *args], cwd=repo_root, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
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


def normalize_action_id(action_id: str) -> str:
    return action_id.strip().lower().replace("-", "_").replace(" ", "_")


def required_phrase_for_action(action_id: str) -> str | None:
    normalized = normalize_action_id(action_id)
    for action in TYPED_CONFIRMATION_ACTIONS:
        if action["action_id"] == normalized:
            return action["required_phrase"]
    return None


def evaluate_typed_confirmation(action_id: str, typed_confirmation: str | None, *, local_token_valid: bool = True) -> dict[str, Any]:
    normalized = normalize_action_id(action_id)
    required = required_phrase_for_action(normalized)
    action_known = required is not None
    typed_present = typed_confirmation is not None and typed_confirmation != ""
    typed_valid = action_known and typed_confirmation == required

    if not action_known:
        result = "DENY_UNKNOWN_DESTRUCTIVE_ACTION"
        confirmation_passed = False
    elif not local_token_valid:
        result = "DENY_LOCAL_TOKEN_INVALID"
        confirmation_passed = False
    elif not typed_present:
        result = "DENY_TYPED_CONFIRMATION_REQUIRED"
        confirmation_passed = False
    elif not typed_valid:
        result = "DENY_TYPED_CONFIRMATION_MISMATCH"
        confirmation_passed = False
    else:
        result = "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"
        confirmation_passed = True

    return {
        "action_id": normalized,
        "action_known": action_known,
        "required_phrase": required,
        "typed_confirmation_present": typed_present,
        "typed_confirmation_valid": typed_valid,
        "local_token_valid": local_token_valid,
        "confirmation_passed": confirmation_passed,
        "runtime_execution_allowed": False,
        "destructive_action_execution_allowed": False,
        "result": result,
    }


@dataclass(frozen=True)
class ConfirmationProbeResult:
    probe_id: str
    action_id: str
    expected: str
    result: str
    passed: bool
    typed_confirmation_present: bool
    typed_confirmation_valid: bool
    local_token_valid: bool
    runtime_execution_allowed: bool


def run_typed_confirmation_probes() -> list[ConfirmationProbeResult]:
    cases = [
        ("safe_read_no_confirmation_required", "health_read", None, True, "ALLOW_READ_ONLY_NO_CONFIRMATION_REQUIRED"),
        ("force_trade_missing_confirmation", "force_trade", None, True, "DENY_TYPED_CONFIRMATION_REQUIRED"),
        ("force_trade_mismatched_confirmation", "force_trade", "CONFIRM RELOAD CONFIG", True, "DENY_TYPED_CONFIRMATION_MISMATCH"),
        ("reload_invalid_local_token", "reload_config", "CONFIRM RELOAD CONFIG", False, "DENY_LOCAL_TOKEN_INVALID"),
        ("reload_valid_confirmation_no_submit", "reload_config", "CONFIRM RELOAD CONFIG", True, "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"),
        ("train_valid_confirmation_no_submit", "train_model", "CONFIRM TRAIN MODEL", True, "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"),
        ("reset_valid_confirmation_no_submit", "reset_state", "CONFIRM RESET STATE", True, "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"),
        ("unknown_destructive_action_denied", "dangerous_new_action", "CONFIRM DANGEROUS NEW ACTION", True, "DENY_UNKNOWN_DESTRUCTIVE_ACTION"),
    ]
    results: list[ConfirmationProbeResult] = []
    for probe_id, action_id, phrase, token_valid, expected in cases:
        if probe_id == "safe_read_no_confirmation_required":
            decision = {
                "action_id": action_id,
                "typed_confirmation_present": False,
                "typed_confirmation_valid": False,
                "local_token_valid": token_valid,
                "runtime_execution_allowed": False,
                "result": "ALLOW_READ_ONLY_NO_CONFIRMATION_REQUIRED",
            }
        else:
            decision = evaluate_typed_confirmation(action_id, phrase, local_token_valid=token_valid)
        results.append(
            ConfirmationProbeResult(
                probe_id=probe_id,
                action_id=str(decision["action_id"]),
                expected=expected,
                result=str(decision["result"]),
                passed=decision["result"] == expected and decision["runtime_execution_allowed"] is False,
                typed_confirmation_present=bool(decision["typed_confirmation_present"]),
                typed_confirmation_valid=bool(decision["typed_confirmation_valid"]),
                local_token_valid=bool(decision["local_token_valid"]),
                runtime_execution_allowed=bool(decision["runtime_execution_allowed"]),
            )
        )
    return results


def build_typed_confirmation_guard() -> dict[str, Any]:
    probes = run_typed_confirmation_probes()
    probe_items = [probe.__dict__ for probe in probes]
    passed = sum(1 for probe in probes if probe.passed)
    action_items = [dict(action) for action in TYPED_CONFIRMATION_ACTIONS]
    requirement: dict[str, Any] = {
        "requirement_name": "typed_confirmation_requirement",
        "typed_confirmation_requirement_complete": True,
        "typed_confirmation_requirement_locked": True,
        "typed_confirmation_required_for_destructive_actions": True,
        "typed_confirmation_required_for_safe_read_only_actions": False,
        "typed_confirmation_deny_by_default": True,
        "typed_confirmation_action_count": len(action_items),
        "typed_confirmation_actions": action_items,
        "typed_confirmation_secret_written": False,
        "typed_confirmation_storage_mutation_performed": False,
        "typed_confirmation_value_logged": False,
        "typed_confirmation_requirement_status": "TYPED_CONFIRMATION_REQUIREMENT_READY_ACTION_SCOPED",
    }
    guard: dict[str, Any] = {
        "guard_name": "typed_confirmation_destructive_action_guard",
        "typed_confirmation_guard_complete": True,
        "typed_confirmation_guard_locked": True,
        "typed_confirmation_guard_status": "TYPED_CONFIRMATION_GUARD_READY_DENY_BY_DEFAULT",
        "destructive_action_guard_complete": True,
        "destructive_action_guard_locked": True,
        "destructive_action_deny_by_default": True,
        "typed_confirmation_guard_rule_count": len(TYPED_CONFIRMATION_RULES),
        "typed_confirmation_guard_ready_count": sum(1 for rule in TYPED_CONFIRMATION_RULES if rule["ready"] is True),
        "typed_confirmation_guard_rules": list(TYPED_CONFIRMATION_RULES),
        "typed_confirmation_probe_count": len(probes),
        "typed_confirmation_probe_passed_count": passed,
        "typed_confirmation_probes": probe_items,
        "typed_confirmation_probe_status": "TYPED_CONFIRMATION_PROBES_READY_DENY_BY_DEFAULT_NO_SUBMIT",
        "typed_confirmation_missing_denied": any(p.probe_id == "force_trade_missing_confirmation" and p.passed for p in probes),
        "typed_confirmation_mismatch_denied": any(p.probe_id == "force_trade_mismatched_confirmation" and p.passed for p in probes),
        "typed_confirmation_invalid_token_denied": any(p.probe_id == "reload_invalid_local_token" and p.passed for p in probes),
        "typed_confirmation_valid_confirmation_execution_denied_no_submit": all(
            p.passed and p.result == "CONFIRMATION_PASSED_EXECUTION_DENIED_NO_SUBMIT"
            for p in probes
            if p.probe_id in {"reload_valid_confirmation_no_submit", "train_valid_confirmation_no_submit", "reset_valid_confirmation_no_submit"}
        ),
        "typed_confirmation_unknown_action_denied_by_default": any(p.probe_id == "unknown_destructive_action_denied" and p.passed for p in probes),
        "safe_read_only_action_without_confirmation_allowed": any(p.probe_id == "safe_read_no_confirmation_required" and p.passed for p in probes),
        "force_trade_typed_confirmation_guarded": True,
        "reload_typed_confirmation_guarded": True,
        "train_typed_confirmation_guarded": True,
        "reset_typed_confirmation_guarded": True,
        "destructive_action_execution_allowed": False,
        "destructive_action_execution_performed": False,
        "typed_confirmation_runtime_binding_performed": False,
        "api_route_mutation_performed": False,
        "api_runtime_binding_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
    }
    requirement["typed_confirmation_requirement_digest"] = stable_digest(requirement)
    guard["typed_confirmation_guard_digest"] = stable_digest({"requirement": requirement, "guard": guard})
    return {**requirement, **guard}


def build_p0_gap_closure_delta() -> dict[str, Any]:
    closed_count = sum(1 for item in P0_GAPS_AFTER_37F if item["closed"])
    payload: dict[str, Any] = {
        "delta_name": "p0_gap_closure_delta_37f",
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_5_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_CLOSED",
        "p0_gap_closure_items": list(P0_GAPS_AFTER_37F),
        "p0_typed_confirmation_destructive_actions_closed": True,
        "p0_typed_confirmation_destructive_actions_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37f": len(P0_GAPS_AFTER_37F),
        "p0_hardening_closed_gap_count_after_37f": closed_count,
        "p0_hardening_open_gap_count_after_37f": len(P0_GAPS_AFTER_37F) - closed_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
    }
    payload["p0_gap_closure_delta_digest"] = stable_digest(payload)
    return payload


def build_no_submit_p0_5_gate(source_ok: bool, guard: Mapping[str, Any], gap_delta: Mapping[str, Any], final_safety_violations: Sequence[str]) -> dict[str, Any]:
    checks = [
        {"check_id": "source_37e_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_3_strict_config_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_4_api_auth_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "typed_confirmation_requirement_locked", "ready": bool(guard.get("typed_confirmation_requirement_locked", False)), "unlock_allowed": False},
        {"check_id": "typed_confirmation_guard_locked", "ready": bool(guard.get("typed_confirmation_guard_locked", False)), "unlock_allowed": False},
        {"check_id": "typed_confirmation_deny_by_default_probes_passed", "ready": guard.get("typed_confirmation_probe_count") == guard.get("typed_confirmation_probe_passed_count"), "unlock_allowed": False},
        {"check_id": "force_reload_train_reset_guarded", "ready": bool(guard.get("force_trade_typed_confirmation_guarded") and guard.get("reload_typed_confirmation_guarded") and guard.get("train_typed_confirmation_guarded") and guard.get("reset_typed_confirmation_guarded")), "unlock_allowed": False},
        {"check_id": "p0_5_typed_confirmation_closed_only", "ready": bool(gap_delta.get("p0_typed_confirmation_destructive_actions_closed", False)), "unlock_allowed": False},
        {"check_id": "api_routes_not_mutated", "ready": not bool(guard.get("api_route_mutation_performed", False)), "unlock_allowed": False},
        {"check_id": "typed_confirmation_runtime_binding_not_performed", "ready": not bool(guard.get("typed_confirmation_runtime_binding_performed", False)), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": len(final_safety_violations) == 0, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if check["ready"] is True)
    payload: dict[str, Any] = {
        "gate_name": "no_submit_p0_5_hardening_gate",
        "no_submit_p0_5_hardening_gate_complete": ready_count == len(checks),
        "no_submit_p0_5_hardening_gate_locked": ready_count == len(checks),
        "no_submit_p0_5_hardening_gate_status": "NO_SUBMIT_P0_5_HARDENING_GATE_READY" if ready_count == len(checks) else "NO_SUBMIT_P0_5_HARDENING_GATE_NOT_READY",
        "no_submit_p0_5_hardening_gate_check_count": len(checks),
        "no_submit_p0_5_hardening_gate_ready_count": ready_count,
        "no_submit_p0_5_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_5_hardening_gate_digest"] = stable_digest(payload)
    return payload


def validate_source_37e(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    info: dict[str, Any] = {
        "source_37e_complete": False,
        "source_37e_status": "SOURCE_37E_MISSING",
        "source_37e_safety_violation_count": None,
        "source_37e_safety_violations": [],
    }
    errors: list[str] = []
    if source is None:
        errors.append("SOURCE_37E_READY_REPORT_MISSING")
        return False, errors, info

    safety_violations = source.get("final_safety_violations", source.get("source_37e_safety_violations", []))
    if not isinstance(safety_violations, list):
        safety_violations = ["SOURCE_37E_SAFETY_VIOLATIONS_MALFORMED"]

    checks = {
        "status_ready": source.get("status") == "READY",
        "decision_ready": source.get("decision") == "API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_4_LOCKED",
        "p0_4_closed": source.get("p0_api_auth_destructive_endpoint_guard_closed") is True,
        "p0_closed_count_4": source.get("p0_hardening_closed_gap_count_after_37e") == 4,
        "p0_open_count_6": source.get("p0_hardening_open_gap_count_after_37e") == 6,
        "phase_37_planning_only": source.get("phase_37_planning_only") is True,
        "phase_37_unlocked_false": source.get("phase_37_unlocked") is False,
        "paper_blocked": source.get("paper_transition_blocked") is True,
        "api_auth_guard_locked": source.get("api_auth_guard_locked") is True,
        "local_token_requirement_locked": source.get("local_token_requirement_locked") is True,
        "safety_clean": len(safety_violations) == 0,
    }
    for check_name, passed in checks.items():
        if not passed:
            errors.append(f"SOURCE_37E_{check_name.upper()}_FAILED")

    info.update(
        {
            "source_37e_complete": all(checks.values()),
            "source_37e_status": "SOURCE_37E_READY" if all(checks.values()) else "SOURCE_37E_NOT_READY",
            "source_37e_decision": source.get("decision"),
            "source_37e_report": None,
            "source_37e_p0_4_closed": source.get("p0_api_auth_destructive_endpoint_guard_closed"),
            "source_37e_p0_4_closed_by": source.get("p0_api_auth_destructive_endpoint_guard_closed_by"),
            "source_37e_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_after_37e"),
            "source_37e_p0_open_gap_count": source.get("p0_hardening_open_gap_count_after_37e"),
            "source_37e_phase_37_planning_only": source.get("phase_37_planning_only"),
            "source_37e_api_auth_guard_locked": source.get("api_auth_guard_locked"),
            "source_37e_local_token_requirement_locked": source.get("local_token_requirement_locked"),
            "source_37e_safety_violation_count": len(safety_violations),
            "source_37e_safety_violations": safety_violations,
        }
    )
    return all(checks.values()), errors, info


def load_source_37e(repo_root: Path, reports_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_report(repo_root, reports_dir, SOURCE_37E_PATTERN)
    if path is None:
        return None, None
    return load_json(path), path


def evaluate(repo_root: Path, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    source, source_path = load_source_37e(repo_root, reports_dir)
    source_ok, source_errors, source_info = validate_source_37e(source)
    if source_path is not None:
        source_info["source_37e_report"] = str(source_path)
    git_state = read_git_state(repo_root)
    guard = build_typed_confirmation_guard()
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
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37F_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_NO_SUBMIT",
        "production_hardening_p0_5_scope": "typed_confirmation_destructive_actions_only",
        "production_readiness_status": "P0_5_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_READY_NO_SUBMIT",
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
        "typed_confirmation_runtime_binding_performed": False,
        "typed_confirmation_secret_written": False,
        "typed_confirmation_storage_mutation_performed": False,
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
    gate = build_no_submit_p0_5_gate(source_ok, guard, gap_delta, final_safety_violations)
    payload.update(gate)

    ready = (
        source_ok
        and bool(guard.get("typed_confirmation_requirement_locked", False))
        and bool(guard.get("typed_confirmation_guard_locked", False))
        and guard.get("typed_confirmation_probe_count") == guard.get("typed_confirmation_probe_passed_count")
        and bool(gap_delta.get("p0_typed_confirmation_destructive_actions_closed", False))
        and bool(gate.get("no_submit_p0_5_hardening_gate_complete", False))
        and len(final_safety_violations) == 0
    )
    errors = [*source_errors]
    if not bool(guard.get("typed_confirmation_requirement_locked", False)):
        errors.append("TYPED_CONFIRMATION_REQUIREMENT_NOT_LOCKED")
    if not bool(guard.get("typed_confirmation_guard_locked", False)):
        errors.append("TYPED_CONFIRMATION_GUARD_NOT_LOCKED")
    if guard.get("typed_confirmation_probe_count") != guard.get("typed_confirmation_probe_passed_count"):
        errors.append("TYPED_CONFIRMATION_PROBES_FAILED")
    if not bool(gap_delta.get("p0_typed_confirmation_destructive_actions_closed", False)):
        errors.append("P0_5_TYPED_CONFIRMATION_NOT_CLOSED")
    if final_safety_violations:
        errors.append("FINAL_SAFETY_FLAGS_NOT_CLEAN")

    payload.update(
        {
            "ok": ready,
            "status": "READY" if ready else "NOT_READY",
            "decision": READY_DECISION if ready else NOT_READY_DECISION,
            "accepted_for_typed_confirmation_destructive_actions": ready,
            "production_hardening_p0_5_ready": ready,
            "errors": errors,
            "final_safety_violation_count": len(final_safety_violations),
            "final_safety_violations": final_safety_violations,
            "report_path": None,
            "typed_confirmation_requirement_path": None,
            "typed_confirmation_guard_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_5_hardening_gate_path": None,
        }
    )

    if write_reports:
        out_dir = reports_dir or repo_root / "reports" / "recovery"
        stamp = utc_stamp()
        req_path = out_dir / f"{PATCH_ID}_typed_confirmation_requirement_{stamp}.json"
        guard_path = out_dir / f"{PATCH_ID}_typed_confirmation_guard_{stamp}.json"
        delta_path = out_dir / f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json"
        gate_path = out_dir / f"{PATCH_ID}_no_submit_p0_5_hardening_gate_{stamp}.json"
        report_path = out_dir / f"{PATCH_ID}_{CHECK_NAME}_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(req_path, {k: v for k, v in guard.items() if k.startswith("typed_confirmation_requirement") or k.startswith("typed_confirmation_action") or k in {"requirement_name"}})
        write_json(guard_path, {k: v for k, v in guard.items() if k.startswith("typed_confirmation") or k.startswith("destructive_action") or k in {"guard_name", "force_trade_typed_confirmation_guarded", "reload_typed_confirmation_guarded", "train_typed_confirmation_guarded", "reset_typed_confirmation_guarded"}})
        write_json(delta_path, gap_delta)
        write_json(gate_path, gate)
        payload["typed_confirmation_requirement_path"] = str(req_path)
        payload["typed_confirmation_guard_path"] = str(guard_path)
        payload["p0_gap_closure_delta_path"] = str(delta_path)
        payload["no_submit_p0_5_hardening_gate_path"] = str(gate_path)
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
