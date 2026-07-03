from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436635E"
PATCH_VERSION = "4B.4.3.6.6.35E"
PATCH_NAME = "Dry-Run Collection Authorization"
CHECK_NAME = "dry_run_collection_authorization"
READY_DECISION = "DRY_RUN_COLLECTION_AUTHORIZATION_READY_NO_SUBMIT_COLLECTION_SEAL_LOCKED"
NOT_READY_DECISION = "DRY_RUN_COLLECTION_AUTHORIZATION_NOT_READY"
SOURCE_READY_DECISION = "COLLECTION_PREFLIGHT_GATE_READY_NO_SUBMIT_EXECUTION_GUARD_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.35F"
SOURCE_PATTERN = "4B436635D_collection_preflight_gate_*_ready.json"

DANGEROUS_TRUE_FIELDS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
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
    "submit_boundary_relaxed",
    "approval_performed",
    "simulated_approval_performed",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "collection_runbook_executed",
    "collection_preflight_executed",
    "public_market_data_collection_performed",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "paper_transition_unblocked",
    "paper_transition_approval_performed",
    "paper_environment_enabled",
    "live_environment_enabled",
    "runtime_readiness_unlock_performed",
    "execution_guard_relaxed",
    "public_data_collection_allowed_now",
    "public_data_permission_granted_for_execution",
)

FALSE_OUTPUT_FIELDS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
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
    "submit_boundary_relaxed",
    "approval_performed",
    "simulated_approval_performed",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "collection_runbook_executed",
    "collection_preflight_executed",
    "public_market_data_collection_performed",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "paper_transition_unblocked",
    "paper_transition_approval_performed",
    "paper_environment_enabled",
    "live_environment_enabled",
    "runtime_readiness_unlock_performed",
    "execution_guard_relaxed",
    "public_data_collection_allowed_now",
    "public_data_permission_granted_for_execution",
    "operator_collection_token_present",
    "operator_collection_token_valid",
    "public_data_dry_run_authorized",
    "dry_run_collection_authorization_performed",
    "collection_authorization_unlocked",
    "collection_seal_relaxed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def bool_value(data: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "ready"}
    return bool(value)


def int_value(data: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def str_value(data: Mapping[str, Any], key: str, default: str = "") -> str:
    value = data.get(key, default)
    return str(value) if value is not None else default


def find_project_root(start: Path | None = None) -> Path:
    base = (start or Path.cwd()).resolve()
    for candidate in (base, *base.parents):
        if (candidate / "src").exists() or (candidate / "reports").exists() or (candidate / ".git").exists():
            return candidate
    return base


def latest_source_report(reports_dir: Path) -> Path | None:
    candidates = sorted(reports_dir.glob(SOURCE_PATTERN))
    if not candidates:
        return None
    return candidates[-1]


def git_output(root: Path, args: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def git_head_short(root: Path) -> str:
    return git_output(root, ["rev-parse", "--short", "HEAD"])


def git_branch(root: Path) -> str:
    return git_output(root, ["branch", "--show-current"])


def safety_violations(data: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    for key in DANGEROUS_TRUE_FIELDS:
        if bool_value(data, key, False):
            violations.append(key)
    return violations


def validate_source_35d(source: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if str_value(source, "status") != "READY":
        errors.append("source_35d_status_not_ready")
    if str_value(source, "decision") != SOURCE_READY_DECISION:
        errors.append("source_35d_decision_mismatch")
    required_true = (
        "source_35c_complete",
        "public_data_permission_ledger_complete",
        "runtime_probe_dry_run_plan_complete",
        "no_submit_execution_guard_complete",
        "no_submit_execution_guard_locked",
        "collection_preflight_ready",
        "paper_transition_blocked",
        "phase_35_planning_only",
    )
    for key in required_true:
        if not bool_value(source, key, False):
            errors.append(f"source_35d_{key}_not_true")
    required_false = (
        "collection_preflight_executable_now",
        "collection_preflight_executed",
        "evidence_collection_started",
        "runtime_evidence_collection_performed",
        "public_market_data_collection_performed",
        "runtime_probe_performed",
        "runtime_health_probe_performed",
        "private_api_access_allowed",
        "private_account_read_performed",
        "paper_transition_unblocked",
        "paper_transition_approval_performed",
        "paper_environment_enabled",
        "live_environment_enabled",
        "submit_boundary_relaxed",
    )
    for key in required_false:
        if bool_value(source, key, False):
            errors.append(f"source_35d_{key}_not_false")
    for key in safety_violations(source):
        errors.append(f"source_35d_safety_violation_{key}")
    return (not errors, errors)


@dataclass(frozen=True)
class EvaluationConfig:
    project_root: Path
    reports_dir: Path
    write_reports: bool = False
    timestamp: str | None = None


def operator_collection_token_ledger(source: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "operator_collection_token_ledger",
        "source_35d_decision": str_value(source, "decision"),
        "operator_collection_token_required": True,
        "operator_collection_token_present": False,
        "operator_collection_token_valid": False,
        "operator_collection_token_status": "OPERATOR_COLLECTION_TOKEN_NOT_PRESENT_DRY_RUN_AUTH_ONLY",
        "operator_collection_token_schema_ready": True,
        "operator_collection_token_scope": "public_data_dry_run_authorization_only",
        "collection_authorization_unlocked": False,
        "dry_run_collection_authorization_performed": False,
        "runtime_evidence_collection_performed": False,
        "public_market_data_collection_performed": False,
        "private_api_access_allowed": False,
        "next_phase_unlock_allowed": False,
    }
    payload["operator_collection_token_ledger_digest"] = stable_digest(payload)
    return payload


def public_data_dry_run_authorization(source: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "public_data_dry_run_authorization",
        "source_public_data_permission_count": int_value(source, "public_data_permission_count", 0),
        "source_public_data_permission_planned": bool_value(source, "public_data_permission_planned", False),
        "source_public_data_permission_granted_for_execution": bool_value(source, "public_data_permission_granted_for_execution", False),
        "public_data_dry_run_authorization_complete": True,
        "public_data_dry_run_authorized": False,
        "public_data_dry_run_authorization_status": "PUBLIC_DATA_DRY_RUN_AUTHORIZATION_READY_TOKEN_ABSENT_NO_EXECUTION",
        "public_data_permission_planned": True,
        "public_data_collection_allowed_now": False,
        "public_market_data_collection_performed": False,
        "evidence_collection_started": False,
        "runtime_probe_performed": False,
        "next_phase_unlock_allowed": False,
    }
    payload["public_data_dry_run_authorization_digest"] = stable_digest(payload)
    return payload


def no_submit_collection_seal(source: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "no_submit_collection_seal",
        "source_no_submit_execution_guard_digest": str_value(source, "no_submit_execution_guard_digest"),
        "no_submit_collection_seal_complete": True,
        "no_submit_collection_sealed": True,
        "no_submit_collection_seal_locked": True,
        "no_submit_collection_seal_status": "NO_SUBMIT_COLLECTION_SEAL_LOCKED_AUTHORIZATION_DRY_RUN_ONLY",
        "collection_seal_relaxed": False,
        "collection_preflight_executable_now": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "order_submit_performed": False,
        "exchange_submit_allowed": False,
        "paper_submit_allowed": False,
        "next_phase_unlock_allowed": False,
    }
    payload["no_submit_collection_seal_digest"] = stable_digest(payload)
    return payload


def evaluate(config: EvaluationConfig) -> dict[str, Any]:
    project_root = config.project_root.resolve()
    reports_dir = config.reports_dir.resolve()
    stamp = config.timestamp or utc_stamp()
    source_path = latest_source_report(reports_dir)
    source: dict[str, Any] = {}
    errors: list[str] = []

    if source_path is None:
        errors.append("source_35d_report_missing")
    else:
        try:
            source = read_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive for malformed operator files
            errors.append(f"source_35d_report_read_error:{exc}")
            source = {}

    source_complete = False
    source_errors: list[str] = []
    if source:
        source_complete, source_errors = validate_source_35d(source)
        errors.extend(source_errors)

    token_ledger = operator_collection_token_ledger(source)
    auth_ledger = public_data_dry_run_authorization(source)
    seal_ledger = no_submit_collection_seal(source)

    operator_collection_token_ledger_complete = True
    public_data_dry_run_authorization_complete = True
    no_submit_collection_seal_complete = True
    no_submit_collection_sealed = True
    no_submit_collection_seal_locked = True

    own_safety_probe: dict[str, Any] = {key: False for key in FALSE_OUTPUT_FIELDS}
    own_safety_violations = safety_violations(own_safety_probe)
    if own_safety_violations:
        errors.extend([f"own_safety_violation_{field}" for field in own_safety_violations])

    ready = bool(
        source_complete
        and operator_collection_token_ledger_complete
        and public_data_dry_run_authorization_complete
        and no_submit_collection_seal_complete
        and no_submit_collection_sealed
        and no_submit_collection_seal_locked
        and not errors
    )

    report_paths: dict[str, str | None] = {
        "operator_collection_token_ledger_path": None,
        "public_data_dry_run_authorization_path": None,
        "no_submit_collection_seal_path": None,
        "report_path": None,
    }

    if config.write_reports:
        token_path = reports_dir / f"{PATCH_ID}_operator_collection_token_ledger_{stamp}.json"
        auth_path = reports_dir / f"{PATCH_ID}_public_data_dry_run_authorization_{stamp}.json"
        seal_path = reports_dir / f"{PATCH_ID}_no_submit_collection_seal_{stamp}.json"
        write_json(token_path, token_ledger)
        write_json(auth_path, auth_ledger)
        write_json(seal_path, seal_ledger)
        report_paths.update(
            {
                "operator_collection_token_ledger_path": str(token_path),
                "public_data_dry_run_authorization_path": str(auth_path),
                "no_submit_collection_seal_path": str(seal_path),
            }
        )

    result: dict[str, Any] = {
        "ok": ready,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "git_available": bool(git_output(project_root, ["rev-parse", "--git-dir"])),
        "git_branch": git_branch(project_root),
        "git_head_short": git_head_short(project_root),
        "errors": errors,
        "source_35d_complete": source_complete,
        "source_35d_status": "SOURCE_35D_READY" if source_complete else "SOURCE_35D_NOT_READY",
        "source_35d_report": str(source_path) if source_path else None,
        "source_35d_decision": str_value(source, "decision"),
        "source_35d_safety_violation_count": len(safety_violations(source)),
        "source_35d_safety_violations": safety_violations(source),
        "source_35d_public_data_permission_count": int_value(source, "public_data_permission_count", 0),
        "source_35d_runtime_probe_dry_run_count": int_value(source, "runtime_probe_dry_run_count", 0),
        "source_35d_no_submit_execution_guard_digest": str_value(source, "no_submit_execution_guard_digest"),
        "phase_34_closed": bool_value(source, "phase_34_closed", False),
        "phase_35_planning_only": True,
        "accepted_for_dry_run_collection_authorization": ready,
        "operator_collection_token_ledger_complete": operator_collection_token_ledger_complete,
        "operator_collection_token_required": True,
        "operator_collection_token_present": False,
        "operator_collection_token_valid": False,
        "operator_collection_token_schema_ready": True,
        "operator_collection_token_status": "OPERATOR_COLLECTION_TOKEN_NOT_PRESENT_DRY_RUN_AUTH_ONLY",
        "operator_collection_token_ledger_digest": token_ledger["operator_collection_token_ledger_digest"],
        "public_data_dry_run_authorization_complete": public_data_dry_run_authorization_complete,
        "public_data_dry_run_authorized": False,
        "public_data_dry_run_authorization_status": "PUBLIC_DATA_DRY_RUN_AUTHORIZATION_READY_TOKEN_ABSENT_NO_EXECUTION",
        "public_data_dry_run_authorization_digest": auth_ledger["public_data_dry_run_authorization_digest"],
        "public_data_permission_planned": True,
        "public_data_collection_allowed_now": False,
        "no_submit_collection_seal_complete": no_submit_collection_seal_complete,
        "no_submit_collection_sealed": no_submit_collection_sealed,
        "no_submit_collection_seal_locked": no_submit_collection_seal_locked,
        "no_submit_collection_seal_status": "NO_SUBMIT_COLLECTION_SEAL_LOCKED_AUTHORIZATION_DRY_RUN_ONLY",
        "no_submit_collection_seal_digest": seal_ledger["no_submit_collection_seal_digest"],
        "collection_authorization_unlocked": False,
        "dry_run_collection_authorization_performed": False,
        "collection_seal_relaxed": False,
        "collection_preflight_executable_now": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "runtime_readiness_status": "DRY_RUN_COLLECTION_AUTHORIZATION_READY_PLANNING_ONLY_NO_SUBMIT" if ready else "DRY_RUN_COLLECTION_AUTHORIZATION_NOT_READY",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_DRY_RUN_AUTH_ONLY_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
    }
    result.update({key: False for key in FALSE_OUTPUT_FIELDS if key not in result})

    if config.write_reports:
        status_suffix = "ready" if ready else "not_ready"
        report_path = reports_dir / f"{PATCH_ID}_dry_run_collection_authorization_{stamp}_{status_suffix}.json"
        result_with_paths = dict(result)
        result_with_paths.update(report_paths)
        result_with_paths["report_path"] = str(report_path)
        write_json(report_path, result_with_paths)
        result = result_with_paths
    else:
        result.update(report_paths)

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve() if args.project_root else find_project_root()
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = project_root / reports_dir
    result = evaluate(EvaluationConfig(project_root=project_root, reports_dir=reports_dir, write_reports=args.write_reports))
    if args.once_json or True:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
