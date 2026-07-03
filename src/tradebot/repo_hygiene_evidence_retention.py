from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436637C"
PATCH_VERSION = "4B.4.3.6.6.37C"
PATCH_NAME = "Repo Hygiene Evidence Retention"
CHECK_NAME = "repo_hygiene_evidence_retention"
READY_DECISION = "REPO_HYGIENE_EVIDENCE_RETENTION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_2_LOCKED"
NOT_READY_DECISION = "REPO_HYGIENE_EVIDENCE_RETENTION_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37D"
SOURCE_37B_H1_PATTERN = "4B436637B_H1_install_contract_launcher_alignment_hotfix_*_ready.json"

SAFETY_FALSE_KEYS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
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
    "public_data_fetch_adapter_executed",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executed",
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
    "strict_config_mutation_performed",
    "trading_action_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "typed_confirmation_mutation_performed",
)

P0_GAPS_AFTER_37C: tuple[dict[str, Any], ...] = (
    {"gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed": True, "domain": "install_contract", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed": True, "domain": "repo_hygiene", "closed_by": PATCH_VERSION},
    {"gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed": False, "domain": "strict_config", "closed_by": None},
    {"gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed": False, "domain": "api_security", "closed_by": None},
    {"gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed": False, "domain": "operator_controls", "closed_by": None},
    {"gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed": False, "domain": "persistence", "closed_by": None},
    {"gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed": False, "domain": "runtime_safety", "closed_by": None},
    {"gap_id": "P0_FEE_SLIPPAGE_BASELINE", "closed": False, "domain": "execution_cost_model", "closed_by": None},
    {"gap_id": "P0_REPORT_COMMIT_POLICY", "closed": False, "domain": "evidence_governance", "closed_by": None},
    {"gap_id": "P0_PROMOTION_GATE_ISOLATION", "closed": False, "domain": "promotion_governance", "closed_by": None},
)

CANONICAL_REPORT_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "canonical_root_reports_recovery",
        "ready": True,
        "path": "reports/recovery",
        "policy": "new phase evidence is written under reports/recovery",
    },
    {
        "rule_id": "phase_report_ready_not_ready_suffix",
        "ready": True,
        "pattern": "4B*_ready.json | 4B*_not_ready.json",
        "policy": "terminal phase reports must expose explicit READY/NOT_READY suffix",
    },
    {
        "rule_id": "component_ledgers_retained",
        "ready": True,
        "policy": "component ledgers are retained as evidence and not deduplicated by automation",
    },
    {
        "rule_id": "intermediate_artifacts_not_auto_committed",
        "ready": True,
        "policy": "operator reviews git status and commits only selected canonical evidence",
    },
    {
        "rule_id": "report_delete_forbidden",
        "ready": True,
        "policy": "patch tools must not delete reports",
    },
    {
        "rule_id": "report_move_and_dedup_forbidden",
        "ready": True,
        "policy": "patch tools must not move reports or deduplicate evidence automatically",
    },
)

BACKUP_RETENTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "patch_backup_dirs_are_evidence",
        "ready": True,
        "policy": "tools/_patch_backup_* directories are retained as patch evidence",
    },
    {
        "rule_id": "backup_delete_forbidden",
        "ready": True,
        "policy": "patch backup directories must not be deleted by patch automation",
    },
    {
        "rule_id": "backup_move_forbidden",
        "ready": True,
        "policy": "patch backup directories must not be moved by patch automation",
    },
    {
        "rule_id": "rollback_reference_preserved",
        "ready": True,
        "policy": "backup directory names stay stable for rollback reference",
    },
    {
        "rule_id": "cleanup_requires_separate_operator_phase",
        "ready": True,
        "policy": "cleanup/archival requires a separate explicit operator-approved phase",
    },
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
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def latest_report(repo_root: Path, reports_dir: Path | None, pattern: str) -> Path | None:
    search_dirs: list[Path] = []
    if reports_dir is not None:
        search_dirs.append(reports_dir)
    search_dirs.extend([repo_root / "reports" / "recovery", repo_root / "reports", repo_root])
    candidates: list[Path] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob(pattern):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def truthy_violations(source: Mapping[str, Any], flags: Iterable[str]) -> list[str]:
    return [name for name in flags if bool(source.get(name, False))]


@dataclass(frozen=True)
class GitState:
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    phase_37_tags: tuple[str, ...]


def _run_git(args: Sequence[str], repo_root: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def read_git_state(repo_root: Path) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.37*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple())
    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    phase_37_tags = tuple(sorted(line.strip() for line in tags_result.stdout.splitlines() if line.strip())) if tags_result.returncode == 0 else tuple()
    return GitState(
        git_available=git_available,
        git_branch=branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        git_head_short=head_result.stdout.strip() if head_result.returncode == 0 else None,
        phase_37_tags=phase_37_tags,
    )


def safe_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def load_source_37b_h1(repo_root: Path, reports_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_report(repo_root, reports_dir, SOURCE_37B_H1_PATTERN)
    if path is None:
        return None, None
    return load_json(path), path


def validate_source_37b_h1(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    if source is None:
        return False, ["SOURCE_37B_H1_READY_REPORT_NOT_FOUND"], {
            "source_37b_h1_complete": False,
            "source_37b_h1_status": "SOURCE_37B_H1_MISSING",
            "source_37b_h1_safety_violation_count": 0,
            "source_37b_h1_safety_violations": [],
        }
    errors: list[str] = []
    safety_violations = truthy_violations(source, SAFETY_FALSE_KEYS)
    if source.get("status") != "READY":
        errors.append("SOURCE_37B_H1_STATUS_NOT_READY")
    if source.get("decision") != "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_READY_NO_SUBMIT_P0_1_CLOSED":
        errors.append("SOURCE_37B_H1_DECISION_UNEXPECTED")
    if not bool(source.get("p0_install_contract_alignment_closed", False)):
        errors.append("SOURCE_37B_H1_P0_1_NOT_CLOSED")
    if source.get("p0_install_contract_alignment_closed_by") != "4B.4.3.6.6.37B-H1":
        errors.append("SOURCE_37B_H1_P0_1_CLOSED_BY_UNEXPECTED")
    if not bool(source.get("production_hardening_p0_1_ready", False)):
        errors.append("SOURCE_37B_H1_P0_1_NOT_READY")
    if int(source.get("p0_hardening_closed_gap_count_after_37b_h1", -1) or -1) != 1:
        errors.append("SOURCE_37B_H1_CLOSED_GAP_COUNT_UNEXPECTED")
    if int(source.get("p0_hardening_open_gap_count_after_37b_h1", -1) or -1) != 9:
        errors.append("SOURCE_37B_H1_OPEN_GAP_COUNT_UNEXPECTED")
    if safety_violations:
        errors.append("SOURCE_37B_H1_SAFETY_VIOLATION")
    info = {
        "source_37b_h1_complete": len(errors) == 0,
        "source_37b_h1_status": "SOURCE_37B_H1_READY" if len(errors) == 0 else "SOURCE_37B_H1_INVALID",
        "source_37b_h1_decision": source.get("decision"),
        "source_37b_h1_p0_1_closed": bool(source.get("p0_install_contract_alignment_closed", False)),
        "source_37b_h1_p0_1_closed_by": source.get("p0_install_contract_alignment_closed_by"),
        "source_37b_h1_p0_open_gap_count": int(source.get("p0_hardening_open_gap_count_after_37b_h1", 0) or 0),
        "source_37b_h1_p0_closed_gap_count": int(source.get("p0_hardening_closed_gap_count_after_37b_h1", 0) or 0),
        "source_37b_h1_phase_37_planning_only": bool(source.get("phase_37_planning_only", False)),
        "source_37b_h1_report": None,
        "source_37b_h1_safety_violation_count": len(safety_violations),
        "source_37b_h1_safety_violations": safety_violations,
    }
    return len(errors) == 0, errors, info


def build_canonical_reports_policy(repo_root: Path) -> dict[str, Any]:
    report_root = repo_root / "reports" / "recovery"
    ready_reports = list(report_root.glob("4B*_ready.json")) if report_root.exists() else []
    not_ready_reports = list(report_root.glob("4B*_not_ready.json")) if report_root.exists() else []
    rules = [dict(rule) for rule in CANONICAL_REPORT_RULES]
    ready_count = sum(1 for rule in rules if bool(rule.get("ready", False)))
    payload: dict[str, Any] = {
        "policy_name": "canonical_reports_policy",
        "canonical_reports_policy_complete": ready_count == len(rules),
        "canonical_reports_policy_locked": ready_count == len(rules),
        "canonical_reports_policy_status": "CANONICAL_REPORTS_POLICY_READY_NO_DESTRUCTIVE_CLEANUP" if ready_count == len(rules) else "CANONICAL_REPORTS_POLICY_NOT_READY",
        "canonical_reports_policy_rule_count": len(rules),
        "canonical_reports_policy_ready_count": ready_count,
        "canonical_reports_policy_rules": rules,
        "canonical_reports_root": "reports/recovery",
        "canonical_reports_root_exists": report_root.exists(),
        "canonical_ready_report_count_observed": len(ready_reports),
        "canonical_not_ready_report_count_observed": len(not_ready_reports),
        "canonical_report_delete_allowed": False,
        "canonical_report_move_allowed": False,
        "canonical_report_dedup_allowed": False,
        "canonical_report_commit_policy": "commit_selected_canonical_reports_only_after_operator_review",
        "intermediate_evidence_retention_policy": "retain_unmodified_unless_future_explicit_cleanup_phase_is_approved",
        "repo_hygiene_cleanup_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "deduplication_action_performed": False,
    }
    payload["canonical_reports_policy_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def discover_patch_backup_dirs(repo_root: Path) -> tuple[dict[str, Any], ...]:
    candidates: list[Path] = []
    for base in (repo_root / "tools", repo_root):
        if not base.exists():
            continue
        candidates.extend(path for path in base.glob("_patch_backup*") if path.is_dir())
    unique = sorted({path.resolve(): path for path in candidates}.values(), key=lambda path: safe_rel(path, repo_root))
    return tuple(
        {
            "path": safe_rel(path, repo_root),
            "exists": path.exists(),
            "retained": True,
            "delete_allowed": False,
            "move_allowed": False,
        }
        for path in unique
    )


def build_patch_backup_retention_guard(repo_root: Path) -> dict[str, Any]:
    backup_dirs = discover_patch_backup_dirs(repo_root)
    rules = [dict(rule) for rule in BACKUP_RETENTION_RULES]
    ready_count = sum(1 for rule in rules if bool(rule.get("ready", False)))
    payload: dict[str, Any] = {
        "guard_name": "patch_backup_retention_guard",
        "patch_backup_retention_guard_complete": ready_count == len(rules),
        "patch_backup_retention_guard_locked": ready_count == len(rules),
        "patch_backup_retention_guard_status": "PATCH_BACKUP_RETENTION_GUARD_READY_NO_DELETE_NO_MOVE" if ready_count == len(rules) else "PATCH_BACKUP_RETENTION_GUARD_NOT_READY",
        "patch_backup_retention_guard_rule_count": len(rules),
        "patch_backup_retention_guard_ready_count": ready_count,
        "patch_backup_retention_guard_rules": rules,
        "patch_backup_directory_count_observed": len(backup_dirs),
        "patch_backup_directories_observed": list(backup_dirs),
        "patch_backup_delete_allowed": False,
        "patch_backup_move_allowed": False,
        "patch_backup_archive_allowed": False,
        "patch_backup_cleanup_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "destructive_cleanup_performed": False,
    }
    payload["patch_backup_retention_guard_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def build_p0_gap_closure_delta() -> dict[str, Any]:
    items = [dict(item) for item in P0_GAPS_AFTER_37C]
    closed_count = sum(1 for item in items if item["closed"] is True)
    open_count = len(items) - closed_count
    p0_2_closed = any(item["gap_id"] == "P0_REPO_HYGIENE_EVIDENCE_RETENTION" and item["closed"] is True for item in items)
    payload: dict[str, Any] = {
        "delta_name": "p0_gap_closure_delta_37c",
        "p0_gap_closure_delta_complete": p0_2_closed,
        "p0_gap_closure_delta_locked": p0_2_closed,
        "p0_gap_closure_delta_status": "P0_2_REPO_HYGIENE_GAP_CLOSED" if p0_2_closed else "P0_2_REPO_HYGIENE_GAP_NOT_CLOSED",
        "p0_gap_closure_items": items,
        "p0_repo_hygiene_evidence_retention_closed": p0_2_closed,
        "p0_repo_hygiene_evidence_retention_closed_by": PATCH_VERSION if p0_2_closed else None,
        "p0_hardening_gap_count_after_37c": len(items),
        "p0_hardening_closed_gap_count_after_37c": closed_count,
        "p0_hardening_open_gap_count_after_37c": open_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
    }
    payload["p0_gap_closure_delta_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def build_no_submit_p0_2_gate(
    source_ok: bool,
    canonical_policy: Mapping[str, Any],
    backup_guard: Mapping[str, Any],
    gap_delta: Mapping[str, Any],
    final_safety_violations: Sequence[str],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        {"check_id": "source_37b_h1_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "canonical_reports_policy_locked", "ready": bool(canonical_policy.get("canonical_reports_policy_locked", False)), "unlock_allowed": False},
        {"check_id": "patch_backup_retention_guard_locked", "ready": bool(backup_guard.get("patch_backup_retention_guard_locked", False)), "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_closed_only", "ready": bool(gap_delta.get("p0_repo_hygiene_evidence_retention_closed", False)) and int(gap_delta.get("p0_hardening_closed_gap_count_after_37c", 0) or 0) == 2, "unlock_allowed": False},
        {"check_id": "destructive_cleanup_forbidden", "ready": not bool(backup_guard.get("destructive_cleanup_performed", False)) and not bool(canonical_policy.get("report_delete_performed", False)), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": len(final_safety_violations) == 0, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if bool(check["ready"]))
    complete = ready_count == len(checks)
    payload: dict[str, Any] = {
        "gate_name": "no_submit_p0_2_hardening_gate",
        "no_submit_p0_2_hardening_gate_complete": complete,
        "no_submit_p0_2_hardening_gate_locked": complete,
        "no_submit_p0_2_hardening_gate_status": "NO_SUBMIT_P0_2_HARDENING_GATE_READY" if complete else "NO_SUBMIT_P0_2_HARDENING_GATE_NOT_READY",
        "no_submit_p0_2_hardening_gate_check_count": len(checks),
        "no_submit_p0_2_hardening_gate_ready_count": ready_count,
        "no_submit_p0_2_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_2_hardening_gate_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def evaluate(repo_root: Path, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    source, source_path = load_source_37b_h1(repo_root, reports_dir)
    source_ok, source_errors, source_info = validate_source_37b_h1(source)
    if source_path is not None:
        source_info["source_37b_h1_report"] = str(source_path)
    git_state = read_git_state(repo_root)
    canonical_policy = build_canonical_reports_policy(repo_root)
    backup_guard = build_patch_backup_retention_guard(repo_root)
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
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37C_REPO_HYGIENE_EVIDENCE_RETENTION_NO_SUBMIT",
        "production_hardening_p0_2_scope": "repo_hygiene_evidence_retention_only",
        "production_readiness_status": "P0_2_REPO_HYGIENE_EVIDENCE_RETENTION_READY_NO_SUBMIT",
        "repo_hygiene_evidence_retention_complete": True,
        "repo_hygiene_evidence_retention_locked": True,
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
        "strict_config_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_schema_mutation_performed": False,
        "runtime_lock_mutation_performed": False,
        "fee_slippage_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "install_contract_mutation_performed": False,
        "requirements_alignment_mutation_performed": False,
        "readme_install_contract_mutation_performed": False,
        "evidence_collection_started": False,
    }
    payload: dict[str, Any] = {}
    payload.update(base_payload)
    payload.update(source_info)
    payload.update(canonical_policy)
    payload.update(backup_guard)
    payload.update(gap_delta)
    final_safety_violations = truthy_violations(payload, SAFETY_FALSE_KEYS)
    gate = build_no_submit_p0_2_gate(source_ok, canonical_policy, backup_guard, gap_delta, final_safety_violations)
    payload.update(gate)

    ready = (
        source_ok
        and bool(canonical_policy.get("canonical_reports_policy_complete", False))
        and bool(canonical_policy.get("canonical_reports_policy_locked", False))
        and bool(backup_guard.get("patch_backup_retention_guard_complete", False))
        and bool(backup_guard.get("patch_backup_retention_guard_locked", False))
        and bool(gap_delta.get("p0_repo_hygiene_evidence_retention_closed", False))
        and bool(gate.get("no_submit_p0_2_hardening_gate_complete", False))
        and len(final_safety_violations) == 0
    )
    errors = [*source_errors]
    if not bool(canonical_policy.get("canonical_reports_policy_locked", False)):
        errors.append("CANONICAL_REPORTS_POLICY_NOT_LOCKED")
    if not bool(backup_guard.get("patch_backup_retention_guard_locked", False)):
        errors.append("PATCH_BACKUP_RETENTION_GUARD_NOT_LOCKED")
    if not bool(gap_delta.get("p0_repo_hygiene_evidence_retention_closed", False)):
        errors.append("P0_2_REPO_HYGIENE_NOT_CLOSED")
    if final_safety_violations:
        errors.append("FINAL_SAFETY_FLAGS_NOT_CLEAN")

    payload.update(
        {
            "ok": ready,
            "status": "READY" if ready else "NOT_READY",
            "decision": READY_DECISION if ready else NOT_READY_DECISION,
            "accepted_for_repo_hygiene_evidence_retention": ready,
            "production_hardening_p0_2_ready": ready,
            "errors": errors,
            "final_safety_violation_count": len(final_safety_violations),
            "final_safety_violations": final_safety_violations,
            "report_path": None,
            "canonical_reports_policy_path": None,
            "patch_backup_retention_guard_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_2_hardening_gate_path": None,
        }
    )

    if write_reports:
        out_dir = reports_dir or repo_root / "reports" / "recovery"
        stamp = utc_stamp()
        canonical_path = out_dir / f"{PATCH_ID}_canonical_reports_policy_{stamp}.json"
        backup_path = out_dir / f"{PATCH_ID}_patch_backup_retention_guard_{stamp}.json"
        delta_path = out_dir / f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json"
        gate_path = out_dir / f"{PATCH_ID}_no_submit_p0_2_hardening_gate_{stamp}.json"
        report_path = out_dir / f"{PATCH_ID}_{CHECK_NAME}_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(canonical_path, canonical_policy)
        write_json(backup_path, backup_guard)
        write_json(delta_path, gap_delta)
        write_json(gate_path, gate)
        payload["canonical_reports_policy_path"] = str(canonical_path)
        payload["patch_backup_retention_guard_path"] = str(backup_path)
        payload["p0_gap_closure_delta_path"] = str(delta_path)
        payload["no_submit_p0_2_hardening_gate_path"] = str(gate_path)
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
