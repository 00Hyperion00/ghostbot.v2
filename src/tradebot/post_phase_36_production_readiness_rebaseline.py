from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436637A"
PATCH_VERSION = "4B.4.3.6.6.37A"
PATCH_NAME = "Post-Phase-36 Production Readiness Re-Baseline"
CHECK_NAME = "post_phase_36_production_readiness_rebaseline"
READY_DECISION = "POST_PHASE_36_PRODUCTION_READINESS_REBASELINE_READY_NO_SUBMIT_37A_PLANNING_GATE_LOCKED"
NOT_READY_DECISION = "POST_PHASE_36_PRODUCTION_READINESS_REBASELINE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37B"
SOURCE_36G_PATTERN = "4B436636G_public_observation_final_closure_*_ready.json"

NO_SUBMIT_FALSE_FLAGS: tuple[str, ...] = (
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
    "file_delete_performed",
    "file_move_performed",
    "http_request_performed",
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
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_fetch_adapter_executed",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executed",
    "public_observation_execution_performed",
    "public_observation_network_off_execution_package_executed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_artifact_written",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "signed_request_performed",
    "simulated_approval_performed",
    "trading_action_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
)

FINAL_FALSE_FLAGS: tuple[str, ...] = NO_SUBMIT_FALSE_FLAGS + (
    "phase_37_unlocked",
    "phase_37_execution_started",
    "p0_hardening_performed",
    "p0_hardening_gap_closed",
    "install_contract_mutation_performed",
    "repo_hygiene_cleanup_performed",
    "strict_config_mutation_performed",
    "api_auth_mutation_performed",
    "typed_confirmation_mutation_performed",
    "sqlite_schema_mutation_performed",
    "runtime_lock_mutation_performed",
    "fee_slippage_mutation_performed",
    "report_commit_policy_mutation_performed",
    "promotion_gate_mutation_performed",
    "paper_transition_approval_performed",
    "live_environment_enabled",
    "paper_environment_enabled",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def latest_report(reports_dir: Path, pattern: str) -> Path | None:
    if not reports_dir.exists():
        return None
    matches = [path for path in reports_dir.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime_ns, path.name))


def truthy_violations(source: Mapping[str, Any], flags: Iterable[str]) -> list[str]:
    return [name for name in flags if bool(source.get(name, False))]


@dataclass(frozen=True)
class GitState:
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    local_phase_36_tags: tuple[str, ...]
    local_phase_37_tags: tuple[str, ...]


def _run_git(args: Sequence[str], cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def read_git_state(repo_root: Path) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        phase36_result = _run_git(["tag", "--list", "4B.4.3.6.6.36*"], repo_root)
        phase37_result = _run_git(["tag", "--list", "4B.4.3.6.6.37*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple(), tuple())

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    phase36_tags = tuple(sorted(line.strip() for line in phase36_result.stdout.splitlines() if line.strip())) if phase36_result.returncode == 0 else tuple()
    phase37_tags = tuple(sorted(line.strip() for line in phase37_result.stdout.splitlines() if line.strip())) if phase37_result.returncode == 0 else tuple()
    return GitState(git_available, branch, head, phase36_tags, phase37_tags)


def build_closed_phase_carryforward(source_36g: Mapping[str, Any]) -> dict[str, Any]:
    closed_phases = [
        {
            "phase": "34",
            "status": "CLOSED",
            "source_field": "phase_34_closed",
            "closed": bool(source_36g.get("phase_34_closed", False)),
            "carryforward_rule": "do_not_reopen_without_new_operator_phase",
        },
        {
            "phase": "35",
            "status": "CLOSED",
            "source_field": "phase_35_closed",
            "closed": bool(source_36g.get("phase_35_closed", False)),
            "carryforward_rule": "phase_35_final_audit_remains_authoritative",
        },
        {
            "phase": "36",
            "status": "FINAL_CLOSED",
            "source_field": "phase_36_final_closed",
            "closed": bool(source_36g.get("phase_36_final_closed", False)),
            "carryforward_rule": "public_observation_final_seal_remains_no_submit",
        },
    ]
    payload: dict[str, Any] = {
        "carryforward_name": "closed_phase_carryforward",
        "closed_phase_carryforward_complete": True,
        "closed_phase_carryforward_locked": True,
        "closed_phase_carryforward_status": "CLOSED_PHASE_CARRYFORWARD_READY_PHASES_34_36_LOCKED",
        "closed_phase_carryforward_phase_count": len(closed_phases),
        "closed_phase_carryforward_closed_count": sum(1 for item in closed_phases if item["closed"] is True),
        "closed_phase_carryforward_items": closed_phases,
        "phase_34_closed": bool(source_36g.get("phase_34_closed", False)),
        "phase_35_closed": bool(source_36g.get("phase_35_closed", False)),
        "phase_36_interim_closed": bool(source_36g.get("phase_36_interim_closed", False)),
        "phase_36_final_closed": bool(source_36g.get("phase_36_final_closed", False)),
        "no_submit_phase_36_final_closed": bool(source_36g.get("no_submit_phase_36_final_closed", False)),
        "public_observation_final_sealed": bool(source_36g.get("public_observation_final_sealed", False)),
        "closed_phase_carryforward_relaxed": False,
        "phase_reopen_allowed": False,
        "phase_reopen_performed": False,
    }
    payload["closed_phase_carryforward_digest"] = stable_digest(payload)
    return payload


def build_p0_hardening_gap_matrix() -> dict[str, Any]:
    gaps: list[dict[str, Any]] = [
        {
            "gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT",
            "domain": "install_contract",
            "risk_level": "P0",
            "objective": "requirements_pyproject_readme_launcher_consistency",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION",
            "domain": "repo_hygiene",
            "risk_level": "P0",
            "objective": "canonical_reports_patch_backup_retention_policy",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED",
            "domain": "strict_config",
            "risk_level": "P0",
            "objective": "yaml_typo_and_unknown_key_hard_error",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD",
            "domain": "api_security",
            "risk_level": "P0",
            "objective": "local_token_and_destructive_endpoint_auth_required",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS",
            "domain": "operator_controls",
            "risk_level": "P0",
            "objective": "typed_confirmation_for_force_trade_reload_train_and_reset_paths",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_SQLITE_AUDIT_BASELINE",
            "domain": "persistence",
            "risk_level": "P0",
            "objective": "wal_busy_timeout_schema_version_integrity_check_backup_hook",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_RUNTIME_PROCESS_LOCK",
            "domain": "runtime_safety",
            "risk_level": "P0",
            "objective": "single_active_bot_process_per_symbol",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_FEE_SLIPPAGE_BASELINE",
            "domain": "execution_cost_model",
            "risk_level": "P0",
            "objective": "minimum_round_trip_cost_floor_and_slippage_baseline",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_REPORT_COMMIT_POLICY",
            "domain": "evidence_governance",
            "risk_level": "P0",
            "objective": "commit_only_canonical_evidence_ignore_intermediate_artifacts",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
        {
            "gap_id": "P0_PROMOTION_GATE_ISOLATION",
            "domain": "promotion_governance",
            "risk_level": "P0",
            "objective": "hypothesis_outputs_cannot_enable_runtime_paper_live_or_order_paths",
            "current_disposition": "open_planning_required",
            "auto_close_allowed": False,
            "mutation_performed": False,
            "paper_live_dependency": True,
        },
    ]
    payload: dict[str, Any] = {
        "matrix_name": "p0_hardening_gap_matrix",
        "p0_hardening_gap_matrix_complete": True,
        "p0_hardening_gap_matrix_locked": True,
        "p0_hardening_gap_matrix_status": "P0_HARDENING_GAP_MATRIX_READY_OPEN_ITEMS_NOT_CLOSED",
        "p0_hardening_gap_count": len(gaps),
        "p0_hardening_open_gap_count": len(gaps),
        "p0_hardening_closed_gap_count": 0,
        "p0_hardening_gap_matrix_items": gaps,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_gap_closed": False,
        "p0_hardening_auto_close_allowed": False,
        "p0_hardening_paper_live_dependency_count": sum(1 for item in gaps if item["paper_live_dependency"] is True),
        "install_contract_mutation_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "strict_config_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_schema_mutation_performed": False,
        "runtime_lock_mutation_performed": False,
        "fee_slippage_mutation_performed": False,
        "report_commit_policy_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
    }
    payload["p0_hardening_gap_matrix_digest"] = stable_digest(payload)
    return payload


def build_no_submit_37a_planning_gate() -> dict[str, Any]:
    gate_checks = [
        {"check_id": "phase_36_final_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "closed_phase_carryforward_locked", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_gap_matrix_locked", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_gaps_remain_open_by_design", "ready": True, "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "live_real_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_and_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
    ]
    payload: dict[str, Any] = {
        "gate_name": "no_submit_37a_planning_gate",
        "no_submit_37a_planning_gate_complete": True,
        "no_submit_37a_planning_gate_locked": True,
        "no_submit_37a_planning_gate_status": "NO_SUBMIT_37A_PLANNING_GATE_READY_NEXT_PHASE_LOCKED",
        "no_submit_37a_planning_gate_check_count": len(gate_checks),
        "no_submit_37a_planning_gate_ready_count": sum(1 for item in gate_checks if item.get("ready") is True),
        "no_submit_37a_planning_gate_checks": gate_checks,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    payload["no_submit_37a_planning_gate_digest"] = stable_digest(payload)
    return payload


def _missing_carryforward_payload() -> dict[str, Any]:
    return {
        "closed_phase_carryforward_complete": False,
        "closed_phase_carryforward_locked": False,
        "closed_phase_carryforward_status": "CLOSED_PHASE_CARRYFORWARD_NOT_READY_SOURCE_MISSING",
        "closed_phase_carryforward_phase_count": 0,
        "closed_phase_carryforward_closed_count": 0,
        "closed_phase_carryforward_relaxed": False,
        "phase_reopen_allowed": False,
        "phase_reopen_performed": False,
        "closed_phase_carryforward_digest": stable_digest({"missing_source_36g": True}),
    }


def _missing_p0_matrix_payload() -> dict[str, Any]:
    return {
        "p0_hardening_gap_matrix_complete": False,
        "p0_hardening_gap_matrix_locked": False,
        "p0_hardening_gap_matrix_status": "P0_HARDENING_GAP_MATRIX_NOT_READY_SOURCE_MISSING",
        "p0_hardening_gap_count": 0,
        "p0_hardening_open_gap_count": 0,
        "p0_hardening_closed_gap_count": 0,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_gap_closed": False,
        "p0_hardening_gap_matrix_digest": stable_digest({"missing_source_36g": True}),
    }


def _missing_planning_gate_payload() -> dict[str, Any]:
    return {
        "no_submit_37a_planning_gate_complete": False,
        "no_submit_37a_planning_gate_locked": False,
        "no_submit_37a_planning_gate_status": "NO_SUBMIT_37A_PLANNING_GATE_NOT_READY_SOURCE_MISSING",
        "no_submit_37a_planning_gate_check_count": 0,
        "no_submit_37a_planning_gate_ready_count": 0,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "no_submit_37a_planning_gate_digest": stable_digest({"missing_source_36g": True}),
    }


def evaluate_post_phase_36_production_readiness_rebaseline(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    reports_dir = reports_dir.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36G_PATTERN)
    source_36g: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36g_report:{SOURCE_36G_PATTERN}")
    else:
        try:
            source_36g = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_36g_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36g, NO_SUBMIT_FALSE_FLAGS) if source_36g else []
    source_36g_complete = (
        bool(source_36g)
        and source_36g.get("status") == "READY"
        and source_36g.get("decision") == "PUBLIC_OBSERVATION_FINAL_CLOSURE_READY_NO_SUBMIT_PHASE_36_FINAL_SEALED"
        and source_36g.get("phase_34_closed") is True
        and source_36g.get("phase_35_closed") is True
        and source_36g.get("phase_36_interim_closed") is True
        and source_36g.get("phase_36_final_closed") is True
        and source_36g.get("no_submit_phase_36_final_closed") is True
        and source_36g.get("public_observation_final_closure_ready") is True
        and source_36g.get("public_observation_final_sealed") is True
        and source_36g.get("phase_36_remote_tag_audit_complete") is True
        and source_36g.get("phase_36_missing_remote_tag_count") == 0
        and len(source_safety_violations) == 0
    )

    carryforward = build_closed_phase_carryforward(source_36g) if source_36g_complete else _missing_carryforward_payload()
    matrix = build_p0_hardening_gap_matrix() if source_36g_complete else _missing_p0_matrix_payload()
    planning_gate = build_no_submit_37a_planning_gate() if source_36g_complete else _missing_planning_gate_payload()

    rebaseline_ready = (
        source_36g_complete
        and bool(carryforward.get("closed_phase_carryforward_complete"))
        and bool(carryforward.get("closed_phase_carryforward_locked"))
        and carryforward.get("closed_phase_carryforward_closed_count") == 3
        and bool(matrix.get("p0_hardening_gap_matrix_complete"))
        and bool(matrix.get("p0_hardening_gap_matrix_locked"))
        and matrix.get("p0_hardening_open_gap_count") == 10
        and matrix.get("p0_hardening_closed_gap_count") == 0
        and bool(planning_gate.get("no_submit_37a_planning_gate_complete"))
        and bool(planning_gate.get("no_submit_37a_planning_gate_locked"))
        and not errors
    )

    status = "READY" if rebaseline_ready else "NOT_READY"
    decision = READY_DECISION if rebaseline_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": rebaseline_ready,
        "status": status,
        "decision": decision,
        "errors": errors,
        "check_name": CHECK_NAME,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "git_available": git_state.git_available,
        "git_branch": git_state.git_branch,
        "git_head_short": git_state.git_head_short,
        "phase_36_tag_count_observed": len(git_state.local_phase_36_tags),
        "phase_36_tags_observed": list(git_state.local_phase_36_tags),
        "phase_37_tag_count_observed": len(git_state.local_phase_37_tags),
        "phase_37_tags_observed": list(git_state.local_phase_37_tags),
        "source_36g_complete": source_36g_complete,
        "source_36g_status": "SOURCE_36G_READY" if source_36g_complete else "SOURCE_36G_NOT_READY",
        "source_36g_report": str(source_path) if source_path else None,
        "source_36g_decision": source_36g.get("decision"),
        "source_36g_safety_violation_count": len(source_safety_violations),
        "source_36g_safety_violations": source_safety_violations,
        "source_36g_phase_34_closed": source_36g.get("phase_34_closed"),
        "source_36g_phase_35_closed": source_36g.get("phase_35_closed"),
        "source_36g_phase_36_interim_closed": source_36g.get("phase_36_interim_closed"),
        "source_36g_phase_36_final_closed": source_36g.get("phase_36_final_closed"),
        "source_36g_no_submit_phase_36_final_seal_digest": source_36g.get("no_submit_phase_36_final_seal_digest"),
        "source_36g_phase_36_remote_tag_audit_digest": source_36g.get("phase_36_remote_tag_audit_digest"),
        "source_36g_source_36f_gate_digest": source_36g.get("source_36f_gate_digest"),
        "source_36g_no_submit_phase_36_final_closed": source_36g.get("no_submit_phase_36_final_closed"),
        "source_36g_public_observation_final_sealed": source_36g.get("public_observation_final_sealed"),
        "phase_34_closed": bool(source_36g.get("phase_34_closed")) if source_36g else False,
        "phase_35_closed": bool(source_36g.get("phase_35_closed")) if source_36g else False,
        "phase_36_interim_closed": bool(source_36g.get("phase_36_interim_closed")) if source_36g else False,
        "phase_36_final_closed": bool(source_36g.get("phase_36_final_closed")) if source_36g else False,
        "phase_37_planning_only": True,
        "production_readiness_rebaseline_complete": rebaseline_ready,
        "production_readiness_rebaseline_ready": rebaseline_ready,
        "runtime_readiness_status": "POST_PHASE_36_PRODUCTION_READINESS_REBASELINE_READY_NO_SUBMIT_P0_GAPS_OPEN" if rebaseline_ready else "POST_PHASE_36_PRODUCTION_READINESS_REBASELINE_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37A_REBASELINE_P0_GAPS_OPEN_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_post_phase_36_production_readiness_rebaseline": rebaseline_ready,
        "closed_phase_carryforward_path": None,
        "p0_hardening_gap_matrix_path": None,
        "no_submit_37a_planning_gate_path": None,
        "report_path": None,
    }
    result.update(carryforward)
    result.update(matrix)
    result.update(planning_gate)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["phase_37_planning_only"] = True
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["next_phase_unlock_allowed"] = False
    result["next_phase_unlock_performed"] = False
    result["transition_to_next_phase_allowed"] = False
    result["transition_to_next_phase_performed"] = False
    result["p0_hardening_complete"] = False
    result["p0_hardening_performed"] = False
    result["p0_hardening_gap_closed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        carryforward_path = reports_dir / f"{PATCH_ID}_closed_phase_carryforward_{stamp}.json"
        matrix_path = reports_dir / f"{PATCH_ID}_p0_hardening_gap_matrix_{stamp}.json"
        planning_gate_path = reports_dir / f"{PATCH_ID}_no_submit_37a_planning_gate_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_post_phase_36_production_readiness_rebaseline_{stamp}_{status.lower()}.json"
        write_json(carryforward_path, carryforward)
        write_json(matrix_path, matrix)
        write_json(planning_gate_path, planning_gate)
        result["closed_phase_carryforward_path"] = str(carryforward_path)
        result["p0_hardening_gap_matrix_path"] = str(matrix_path)
        result["no_submit_37a_planning_gate_path"] = str(planning_gate_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write carryforward, gap matrix and planning gate reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
