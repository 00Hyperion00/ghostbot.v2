from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636D"
PATCH_VERSION = "4B.4.3.6.6.36D"
PATCH_NAME = "Public Observation Execution Authorization"
CHECK_NAME = "public_observation_execution_authorization"
READY_DECISION = "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_READY_NETWORK_OFF_NO_SUBMIT_SEALED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36E"
SOURCE_36C_PATTERN = "4B436636C_public_observation_dry_run_collector_*_ready.json"

NO_SUBMIT_FALSE_FLAGS: tuple[str, ...] = (
    "approval_performed",
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
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "no_submit_runtime_evidence_guard_relaxed",
    "observation_artifact_validation_performed",
    "observation_artifact_written",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_collection_allowed_now",
    "public_data_fetch_adapter_executed",
    "public_data_observation_allowed_now",
    "public_endpoint_execution_allowed_now",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executable_now",
    "public_observation_dry_run_collector_executed",
    "public_observation_execution_allowed_now",
    "public_observation_execution_performed",
    "read_only_public_data_fetch_adapter_relaxed",
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

FINAL_FALSE_FLAGS: tuple[str, ...] = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "network_submit_allowed",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_overlay_allowed",
    "order_submit_performed",
    "exchange_submit_performed",
    "trading_action_performed",
    "training_performed",
    "reload_performed",
    "runtime_overlay_activated",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "runtime_evidence_artifact_written",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "public_observation_dry_run_collector_executed",
    "public_data_fetch_adapter_executed",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "archive_execution_allowed",
    "archive_move_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "destructive_cleanup_performed",
    "deduplication_action_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "paper_environment_enabled",
    "live_environment_enabled",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "operator_observation_token_present",
    "operator_observation_token_validated",
    "operator_observation_authorization_unlocked",
    "network_off_safety_override_relaxed",
    "network_off_safety_override_consumed",
    "no_submit_execution_seal_relaxed",
    "public_observation_execution_authorized_now",
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
        tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.36*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple())

    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    tags = tuple(sorted(line.strip() for line in tags_result.stdout.splitlines() if line.strip())) if tags_result.returncode == 0 else tuple()
    return GitState(git_available, branch, head, tags)


def build_operator_observation_token(source_36c: Mapping[str, Any]) -> dict[str, Any]:
    template = {
        "token_file": "reports/recovery/operator_observation_token_4B436636D.json",
        "required_phrase": "AUTHORIZE_PUBLIC_OBSERVATION_NETWORK_OFF_NO_SUBMIT",
        "operator_id_required": True,
        "token_ttl_sec": 900,
        "allowed_use": "future_public_observation_authorization_review_only",
        "forbidden_uses": [
            "exchange_submit",
            "network_submit",
            "paper_transition_unlock",
            "runtime_overlay_activation",
            "private_api_access",
            "live_real_activation",
        ],
    }
    payload: dict[str, Any] = {
        "ledger_name": "operator_observation_token",
        "operator_observation_token_ledger_complete": True,
        "operator_observation_token_template_complete": True,
        "operator_observation_token_required": True,
        "operator_observation_token_present": False,
        "operator_observation_token_validated": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_status": "TOKEN_TEMPLATE_READY_TOKEN_NOT_PRESENT_NO_EXECUTION",
        "operator_observation_token_template": template,
        "operator_observation_token_template_digest": stable_digest(template),
        "source_36c_no_submit_runtime_evidence_guard_digest": source_36c.get("no_submit_runtime_evidence_guard_digest"),
        "source_36c_read_only_public_data_fetch_adapter_digest": source_36c.get("read_only_public_data_fetch_adapter_digest"),
        "source_36c_observation_artifact_writer_digest": source_36c.get("observation_artifact_writer_digest"),
        "approval_performed": False,
        "simulated_approval_performed": False,
    }
    payload["operator_observation_token_ledger_digest"] = stable_digest(payload)
    return payload


def build_network_off_safety_override(source_36c: Mapping[str, Any]) -> dict[str, Any]:
    checks = [
        {"check_id": "source_36c_ready", "ready": True, "network_allowed": False},
        {"check_id": "operator_token_template_only", "ready": True, "network_allowed": False},
        {"check_id": "network_requests_forbidden", "ready": True, "network_allowed": False},
        {"check_id": "http_requests_forbidden", "ready": True, "network_allowed": False},
        {"check_id": "signed_requests_forbidden", "ready": True, "network_allowed": False},
        {"check_id": "private_api_forbidden", "ready": True, "network_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "network_allowed": False},
    ]
    payload: dict[str, Any] = {
        "ledger_name": "network_off_safety_override",
        "network_off_safety_override_ledger_complete": True,
        "network_off_safety_override_locked": True,
        "network_off_safety_override_status": "NETWORK_OFF_SAFETY_OVERRIDE_LOCKED_NO_NETWORK_EXECUTION",
        "network_off_safety_override_check_count": len(checks),
        "network_off_safety_override_ready_count": sum(1 for item in checks if item.get("ready") is True),
        "network_off_safety_override_checks": checks,
        "network_off_safety_override_relaxed": False,
        "network_off_safety_override_consumed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_data_fetch_adapter_executed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "source_36c_runtime_readiness_status": source_36c.get("runtime_readiness_status"),
    }
    payload["network_off_safety_override_ledger_digest"] = stable_digest(payload)
    return payload


def build_no_submit_execution_seal(source_36c: Mapping[str, Any]) -> dict[str, Any]:
    seal_checks = [
        {"check_id": "exchange_submit_forbidden", "sealed": True},
        {"check_id": "network_submit_forbidden", "sealed": True},
        {"check_id": "order_submit_forbidden", "sealed": True},
        {"check_id": "paper_transition_forbidden", "sealed": True},
        {"check_id": "runtime_overlay_forbidden", "sealed": True},
        {"check_id": "training_reload_forbidden", "sealed": True},
        {"check_id": "destructive_file_actions_forbidden", "sealed": True},
    ]
    payload: dict[str, Any] = {
        "seal_name": "no_submit_execution_seal",
        "no_submit_execution_seal_complete": True,
        "no_submit_execution_seal_locked": True,
        "no_submit_execution_seal_status": "NO_SUBMIT_EXECUTION_SEAL_LOCKED_AUTHORIZATION_ONLY",
        "no_submit_execution_seal_check_count": len(seal_checks),
        "no_submit_execution_seal_locked_count": sum(1 for item in seal_checks if item.get("sealed") is True),
        "no_submit_execution_seal_checks": seal_checks,
        "no_submit_execution_seal_relaxed": False,
        "public_observation_execution_authorization_ready": True,
        "public_observation_execution_authorized_now": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "public_observation_dry_run_collector_executed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "observation_artifact_written": False,
        "runtime_evidence_artifact_written": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "source_36c_public_observation_dry_run_collector_ready": source_36c.get("public_observation_dry_run_collector_ready"),
    }
    payload["no_submit_execution_seal_digest"] = stable_digest(payload)
    return payload


def _build_missing_token_payload() -> dict[str, Any]:
    return {
        "operator_observation_token_ledger_complete": False,
        "operator_observation_token_template_complete": False,
        "operator_observation_token_required": True,
        "operator_observation_token_present": False,
        "operator_observation_token_validated": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_status": "TOKEN_TEMPLATE_NOT_READY_SOURCE_MISSING",
        "operator_observation_token_ledger_digest": stable_digest({"missing_source_36c": True}),
    }


def _build_missing_network_override_payload() -> dict[str, Any]:
    return {
        "network_off_safety_override_ledger_complete": False,
        "network_off_safety_override_locked": False,
        "network_off_safety_override_status": "NETWORK_OFF_SAFETY_OVERRIDE_NOT_READY_SOURCE_MISSING",
        "network_off_safety_override_check_count": 0,
        "network_off_safety_override_ready_count": 0,
        "network_off_safety_override_relaxed": False,
        "network_off_safety_override_consumed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "network_off_safety_override_ledger_digest": stable_digest({"missing_source_36c": True}),
    }


def _build_missing_seal_payload() -> dict[str, Any]:
    return {
        "no_submit_execution_seal_complete": False,
        "no_submit_execution_seal_locked": False,
        "no_submit_execution_seal_status": "NO_SUBMIT_EXECUTION_SEAL_NOT_READY_SOURCE_MISSING",
        "no_submit_execution_seal_check_count": 0,
        "no_submit_execution_seal_locked_count": 0,
        "no_submit_execution_seal_relaxed": False,
        "public_observation_execution_authorization_ready": False,
        "public_observation_execution_authorized_now": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "no_submit_execution_seal_digest": stable_digest({"missing_source_36c": True}),
    }


def evaluate_public_observation_execution_authorization(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36C_PATTERN)
    source_36c: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36c_report:{SOURCE_36C_PATTERN}")
    else:
        try:
            source_36c = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_36c_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36c, NO_SUBMIT_FALSE_FLAGS) if source_36c else []
    source_36c_complete = (
        bool(source_36c)
        and source_36c.get("status") == "READY"
        and source_36c.get("decision") == "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_READY_NO_SUBMIT_RUNTIME_EVIDENCE_GUARD_LOCKED"
        and source_36c.get("phase_35_closed") is True
        and source_36c.get("phase_36_planning_only") is True
        and source_36c.get("source_36b_complete") is True
        and source_36c.get("read_only_public_data_fetch_adapter_complete") is True
        and source_36c.get("read_only_public_data_fetch_adapter_locked") is True
        and source_36c.get("observation_artifact_writer_complete") is True
        and source_36c.get("observation_artifact_writer_locked") is True
        and source_36c.get("no_submit_runtime_evidence_guard_complete") is True
        and source_36c.get("no_submit_runtime_evidence_guard_locked") is True
        and source_36c.get("public_observation_dry_run_collector_ready") is True
        and len(source_safety_violations) == 0
    )

    token = build_operator_observation_token(source_36c) if source_36c_complete else _build_missing_token_payload()
    network_override = build_network_off_safety_override(source_36c) if source_36c_complete else _build_missing_network_override_payload()
    seal = build_no_submit_execution_seal(source_36c) if source_36c_complete else _build_missing_seal_payload()

    authorization_ready = (
        source_36c_complete
        and bool(token.get("operator_observation_token_ledger_complete"))
        and bool(token.get("operator_observation_token_template_complete"))
        and bool(network_override.get("network_off_safety_override_ledger_complete"))
        and bool(network_override.get("network_off_safety_override_locked"))
        and bool(seal.get("no_submit_execution_seal_complete"))
        and bool(seal.get("no_submit_execution_seal_locked"))
        and not errors
    )

    status = "READY" if authorization_ready else "NOT_READY"
    decision = READY_DECISION if authorization_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": authorization_ready,
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
        "source_36c_complete": source_36c_complete,
        "source_36c_status": "SOURCE_36C_READY" if source_36c_complete else "SOURCE_36C_NOT_READY",
        "source_36c_report": str(source_path) if source_path else None,
        "source_36c_decision": source_36c.get("decision"),
        "source_36c_safety_violation_count": len(source_safety_violations),
        "source_36c_safety_violations": source_safety_violations,
        "source_36c_phase_35_closed": source_36c.get("phase_35_closed"),
        "source_36c_phase_36_planning_only": source_36c.get("phase_36_planning_only"),
        "source_36c_read_only_public_data_fetch_adapter_digest": source_36c.get("read_only_public_data_fetch_adapter_digest"),
        "source_36c_observation_artifact_writer_digest": source_36c.get("observation_artifact_writer_digest"),
        "source_36c_no_submit_runtime_evidence_guard_digest": source_36c.get("no_submit_runtime_evidence_guard_digest"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36c.get("phase_35_closed")) if source_36c else False,
        "phase_36_planning_only": True,
        "public_observation_execution_authorization_ready": authorization_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_READY_NETWORK_OFF_NO_SUBMIT" if authorization_ready else "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_AUTHORIZATION_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_execution_authorization": authorization_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "operator_observation_token_path": None,
        "network_off_safety_override_ledger_path": None,
        "no_submit_execution_seal_path": None,
        "report_path": None,
    }
    result.update(token)
    result.update(network_override)
    result.update(seal)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["operator_observation_token_present"] = False
    result["operator_observation_token_validated"] = False
    result["operator_observation_authorization_unlocked"] = False
    result["public_observation_execution_authorized_now"] = False
    result["public_observation_execution_allowed_now"] = False
    result["network_request_allowed_now"] = False
    result["network_request_performed"] = False
    result["http_request_performed"] = False
    result["signed_request_performed"] = False
    result["no_submit_execution_seal_relaxed"] = False
    result["network_off_safety_override_relaxed"] = False
    result["network_off_safety_override_consumed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        token_path = reports_dir / f"{PATCH_ID}_operator_observation_token_{stamp}.json"
        override_path = reports_dir / f"{PATCH_ID}_network_off_safety_override_ledger_{stamp}.json"
        seal_path = reports_dir / f"{PATCH_ID}_no_submit_execution_seal_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_execution_authorization_{stamp}_{status.lower()}.json"
        write_json(token_path, token)
        write_json(override_path, network_override)
        write_json(seal_path, seal)
        result["operator_observation_token_path"] = str(token_path)
        result["network_off_safety_override_ledger_path"] = str(override_path)
        result["no_submit_execution_seal_path"] = str(seal_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write token, override and seal reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_execution_authorization(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
