from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636E"
PATCH_VERSION = "4B.4.3.6.6.36E"
PATCH_NAME = "Public Observation Network-Off Execution Package"
CHECK_NAME = "public_observation_network_off_execution_package"
READY_DECISION = "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_READY_NO_NETWORK_DRY_RUN_EVIDENCE_SEALED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36F"
SOURCE_36D_PATTERN = "4B436636D_public_observation_execution_authorization_*_ready.json"
DEFAULT_TOKEN_FILE = "reports/recovery/operator_observation_token_4B436636D.json"

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
    "network_off_safety_override_consumed",
    "network_off_safety_override_relaxed",
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "no_submit_execution_seal_relaxed",
    "observation_artifact_written",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_present",
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
    "public_observation_execution_allowed_now",
    "public_observation_execution_authorized_now",
    "public_observation_execution_performed",
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
    "network_request_allowed_now",
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
    "operator_observation_token_consumed",
    "operator_observation_token_validated",
    "operator_observation_authorization_unlocked",
    "public_observation_execution_authorized_now",
    "public_observation_execution_allowed_now",
    "public_observation_network_off_execution_package_executed",
    "no_network_collector_simulation_executed",
    "observation_artifact_written",
    "observation_dry_run_evidence_unsealed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def resolve_token_file(repo_root: Path, source_36d: Mapping[str, Any]) -> Path:
    template = source_36d.get("operator_observation_token_template")
    token_file = DEFAULT_TOKEN_FILE
    if isinstance(template, Mapping):
        raw = template.get("token_file")
        if isinstance(raw, str) and raw.strip():
            token_file = raw.strip()
    path = Path(token_file)
    if not path.is_absolute():
        path = repo_root / path
    return path


def build_token_presence_audit(repo_root: Path, source_36d: Mapping[str, Any]) -> dict[str, Any]:
    token_path = resolve_token_file(repo_root, source_36d)
    exists = token_path.exists() and token_path.is_file()
    payload_parse_ok = False
    payload_keys: list[str] = []
    parse_error: str | None = None
    token_digest: str | None = None
    token_size_bytes = 0
    if exists:
        try:
            token_size_bytes = token_path.stat().st_size
            token_digest = file_sha256(token_path)
            parsed = load_json(token_path)
            payload_parse_ok = True
            payload_keys = sorted(str(key) for key in parsed.keys())
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            parse_error = f"{type(exc).__name__}: {exc}"
    audit_status = "TOKEN_PRESENT_AUDITED_NOT_CONSUMED" if exists else "TOKEN_ABSENT_AUDITED_NO_EXECUTION"
    payload: dict[str, Any] = {
        "audit_name": "token_presence_audit",
        "token_presence_audit_complete": True,
        "token_presence_audit_locked": True,
        "token_presence_audit_status": audit_status,
        "operator_observation_token_file": str(token_path),
        "operator_observation_token_present_actual": exists,
        "operator_observation_token_payload_parse_ok": payload_parse_ok,
        "operator_observation_token_payload_keys": payload_keys,
        "operator_observation_token_payload_parse_error": parse_error,
        "operator_observation_token_payload_digest": token_digest,
        "operator_observation_token_payload_size_bytes": token_size_bytes,
        "operator_observation_token_required": True,
        "operator_observation_token_present": False,
        "operator_observation_token_validated": False,
        "operator_observation_token_consumed": False,
        "operator_observation_authorization_unlocked": False,
        "operator_observation_token_allowed_use": "audit_only_no_unlock",
        "source_36d_operator_observation_token_ledger_digest": source_36d.get("operator_observation_token_ledger_digest"),
        "source_36d_operator_observation_token_template_digest": source_36d.get("operator_observation_token_template_digest"),
    }
    payload["token_presence_audit_digest"] = stable_digest(payload)
    return payload


def build_no_network_collector_simulation(source_36d: Mapping[str, Any]) -> dict[str, Any]:
    scopes = [
        "public_exchange_info_snapshot",
        "public_klines_observation",
        "public_mark_price_observation",
        "public_book_ticker_observation",
    ]
    records = [
        {
            "simulation_scope_id": scope,
            "simulation_mode": "NO_NETWORK_STATIC_CONTRACT_REPLAY",
            "network_required": False,
            "network_allowed": False,
            "network_request_performed": False,
            "http_request_performed": False,
            "signed_request_performed": False,
            "private_api_required": False,
            "order_submit_allowed": False,
            "market_payload_captured": False,
            "observation_artifact_written": False,
            "simulated_result": "CONTRACT_REPLAY_ONLY",
        }
        for scope in scopes
    ]
    payload: dict[str, Any] = {
        "simulation_name": "no_network_collector_simulation",
        "no_network_collector_simulation_complete": True,
        "no_network_collector_simulation_locked": True,
        "no_network_collector_simulation_status": "NO_NETWORK_COLLECTOR_SIMULATION_READY_NO_FETCH",
        "no_network_collector_simulation_mode": "STATIC_CONTRACT_REPLAY_NO_HTTP",
        "no_network_collector_simulation_record_count": len(records),
        "no_network_collector_simulation_records": records,
        "no_network_collector_simulation_executed": False,
        "public_observation_network_off_execution_package_executed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_data_fetch_adapter_executed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "observation_artifact_written": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "source_36d_network_off_safety_override_ledger_digest": source_36d.get("network_off_safety_override_ledger_digest"),
    }
    payload["no_network_collector_simulation_digest"] = stable_digest(payload)
    return payload


def build_observation_execution_dry_run_evidence_seal(
    source_36d: Mapping[str, Any],
    token_audit: Mapping[str, Any],
    simulation: Mapping[str, Any],
) -> dict[str, Any]:
    seal_checks = [
        {"check_id": "source_36d_ready", "sealed": True},
        {"check_id": "token_presence_audited", "sealed": bool(token_audit.get("token_presence_audit_complete"))},
        {"check_id": "token_not_consumed", "sealed": not bool(token_audit.get("operator_observation_token_consumed"))},
        {"check_id": "collector_simulation_no_network", "sealed": bool(simulation.get("no_network_collector_simulation_complete"))},
        {"check_id": "network_request_forbidden", "sealed": not bool(simulation.get("network_request_performed"))},
        {"check_id": "observation_artifact_not_written", "sealed": not bool(simulation.get("observation_artifact_written"))},
        {"check_id": "submit_path_forbidden", "sealed": True},
        {"check_id": "paper_transition_remains_blocked", "sealed": True},
    ]
    locked_count = sum(1 for item in seal_checks if item.get("sealed") is True)
    complete = locked_count == len(seal_checks)
    payload: dict[str, Any] = {
        "seal_name": "observation_execution_dry_run_evidence_seal",
        "observation_execution_dry_run_evidence_seal_complete": complete,
        "observation_execution_dry_run_evidence_seal_locked": complete,
        "observation_execution_dry_run_evidence_seal_status": "OBSERVATION_EXECUTION_DRY_RUN_EVIDENCE_SEALED_NO_NETWORK" if complete else "OBSERVATION_EXECUTION_DRY_RUN_EVIDENCE_SEAL_NOT_READY",
        "observation_execution_dry_run_evidence_seal_check_count": len(seal_checks),
        "observation_execution_dry_run_evidence_seal_locked_count": locked_count,
        "observation_execution_dry_run_evidence_seal_checks": seal_checks,
        "observation_dry_run_evidence_unsealed": False,
        "public_observation_network_off_execution_package_ready": complete,
        "public_observation_network_off_execution_package_executed": False,
        "public_observation_execution_authorized_now": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "runtime_evidence_artifact_written": False,
        "observation_artifact_written": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
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
        "source_36d_no_submit_execution_seal_digest": source_36d.get("no_submit_execution_seal_digest"),
        "token_presence_audit_digest": token_audit.get("token_presence_audit_digest"),
        "no_network_collector_simulation_digest": simulation.get("no_network_collector_simulation_digest"),
    }
    payload["observation_execution_dry_run_evidence_seal_digest"] = stable_digest(payload)
    return payload


def _missing_token_audit() -> dict[str, Any]:
    return {
        "token_presence_audit_complete": False,
        "token_presence_audit_locked": False,
        "token_presence_audit_status": "TOKEN_PRESENCE_AUDIT_NOT_READY_SOURCE_MISSING",
        "operator_observation_token_present_actual": False,
        "operator_observation_token_present": False,
        "operator_observation_token_validated": False,
        "operator_observation_token_consumed": False,
        "operator_observation_authorization_unlocked": False,
        "token_presence_audit_digest": stable_digest({"missing_source_36d": True}),
    }


def _missing_simulation() -> dict[str, Any]:
    return {
        "no_network_collector_simulation_complete": False,
        "no_network_collector_simulation_locked": False,
        "no_network_collector_simulation_status": "NO_NETWORK_COLLECTOR_SIMULATION_NOT_READY_SOURCE_MISSING",
        "no_network_collector_simulation_record_count": 0,
        "no_network_collector_simulation_executed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "public_market_data_collection_performed": False,
        "observation_artifact_written": False,
        "no_network_collector_simulation_digest": stable_digest({"missing_source_36d": True}),
    }


def _missing_seal() -> dict[str, Any]:
    return {
        "observation_execution_dry_run_evidence_seal_complete": False,
        "observation_execution_dry_run_evidence_seal_locked": False,
        "observation_execution_dry_run_evidence_seal_status": "OBSERVATION_EXECUTION_DRY_RUN_EVIDENCE_SEAL_NOT_READY_SOURCE_MISSING",
        "observation_execution_dry_run_evidence_seal_check_count": 0,
        "observation_execution_dry_run_evidence_seal_locked_count": 0,
        "observation_dry_run_evidence_unsealed": False,
        "public_observation_network_off_execution_package_ready": False,
        "public_observation_network_off_execution_package_executed": False,
        "observation_execution_dry_run_evidence_seal_digest": stable_digest({"missing_source_36d": True}),
    }


def evaluate_public_observation_network_off_execution_package(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36D_PATTERN)
    source_36d: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36d_report:{SOURCE_36D_PATTERN}")
    else:
        try:
            source_36d = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_36d_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36d, NO_SUBMIT_FALSE_FLAGS) if source_36d else []
    source_36d_complete = (
        bool(source_36d)
        and source_36d.get("status") == "READY"
        and source_36d.get("decision") == "PUBLIC_OBSERVATION_EXECUTION_AUTHORIZATION_READY_NETWORK_OFF_NO_SUBMIT_SEALED"
        and source_36d.get("phase_35_closed") is True
        and source_36d.get("phase_36_planning_only") is True
        and source_36d.get("source_36c_complete") is True
        and source_36d.get("operator_observation_token_ledger_complete") is True
        and source_36d.get("operator_observation_token_template_complete") is True
        and source_36d.get("operator_observation_authorization_unlocked") is False
        and source_36d.get("network_off_safety_override_ledger_complete") is True
        and source_36d.get("network_off_safety_override_locked") is True
        and source_36d.get("no_submit_execution_seal_complete") is True
        and source_36d.get("no_submit_execution_seal_locked") is True
        and source_36d.get("public_observation_execution_authorization_ready") is True
        and len(source_safety_violations) == 0
    )

    token_audit = build_token_presence_audit(repo_root, source_36d) if source_36d_complete else _missing_token_audit()
    simulation = build_no_network_collector_simulation(source_36d) if source_36d_complete else _missing_simulation()
    dry_run_seal = build_observation_execution_dry_run_evidence_seal(source_36d, token_audit, simulation) if source_36d_complete else _missing_seal()

    package_ready = (
        source_36d_complete
        and bool(token_audit.get("token_presence_audit_complete"))
        and bool(token_audit.get("token_presence_audit_locked"))
        and not bool(token_audit.get("operator_observation_token_consumed"))
        and not bool(token_audit.get("operator_observation_authorization_unlocked"))
        and bool(simulation.get("no_network_collector_simulation_complete"))
        and bool(simulation.get("no_network_collector_simulation_locked"))
        and bool(dry_run_seal.get("observation_execution_dry_run_evidence_seal_complete"))
        and bool(dry_run_seal.get("observation_execution_dry_run_evidence_seal_locked"))
        and not errors
    )

    status = "READY" if package_ready else "NOT_READY"
    decision = READY_DECISION if package_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": package_ready,
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
        "source_36d_complete": source_36d_complete,
        "source_36d_status": "SOURCE_36D_READY" if source_36d_complete else "SOURCE_36D_NOT_READY",
        "source_36d_report": str(source_path) if source_path else None,
        "source_36d_decision": source_36d.get("decision"),
        "source_36d_safety_violation_count": len(source_safety_violations),
        "source_36d_safety_violations": source_safety_violations,
        "source_36d_phase_35_closed": source_36d.get("phase_35_closed"),
        "source_36d_phase_36_planning_only": source_36d.get("phase_36_planning_only"),
        "source_36d_operator_observation_token_ledger_digest": source_36d.get("operator_observation_token_ledger_digest"),
        "source_36d_network_off_safety_override_ledger_digest": source_36d.get("network_off_safety_override_ledger_digest"),
        "source_36d_no_submit_execution_seal_digest": source_36d.get("no_submit_execution_seal_digest"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36d.get("phase_35_closed")) if source_36d else False,
        "phase_36_planning_only": True,
        "public_observation_network_off_execution_package_ready": package_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_READY_NO_NETWORK_NO_SUBMIT" if package_ready else "PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_NETWORK_OFF_EXECUTION_PACKAGE_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_network_off_execution_package": package_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "token_presence_audit_path": None,
        "no_network_collector_simulation_path": None,
        "observation_execution_dry_run_evidence_seal_path": None,
        "report_path": None,
    }
    result.update(token_audit)
    result.update(simulation)
    result.update(dry_run_seal)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["operator_observation_token_validated"] = False
    result["operator_observation_token_consumed"] = False
    result["operator_observation_authorization_unlocked"] = False
    result["public_observation_execution_authorized_now"] = False
    result["public_observation_execution_allowed_now"] = False
    result["public_observation_execution_performed"] = False
    result["network_request_allowed_now"] = False
    result["network_request_performed"] = False
    result["http_request_performed"] = False
    result["signed_request_performed"] = False
    result["observation_artifact_written"] = False
    result["runtime_evidence_artifact_written"] = False
    result["observation_dry_run_evidence_unsealed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        token_path = reports_dir / f"{PATCH_ID}_token_presence_audit_{stamp}.json"
        simulation_path = reports_dir / f"{PATCH_ID}_no_network_collector_simulation_{stamp}.json"
        seal_path = reports_dir / f"{PATCH_ID}_observation_execution_dry_run_evidence_seal_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_network_off_execution_package_{stamp}_{status.lower()}.json"
        write_json(token_path, token_audit)
        write_json(simulation_path, simulation)
        write_json(seal_path, dry_run_seal)
        result["token_presence_audit_path"] = str(token_path)
        result["no_network_collector_simulation_path"] = str(simulation_path)
        result["observation_execution_dry_run_evidence_seal_path"] = str(seal_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write token audit, simulation and seal reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_network_off_execution_package(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
