from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636B"
PATCH_VERSION = "4B.4.3.6.6.36B"
PATCH_NAME = "Public Observation Execution Preflight"
CHECK_NAME = "public_observation_execution_preflight"
READY_DECISION = "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_READY_NO_SUBMIT_EXECUTION_READINESS_GATE_LOCKED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36C"
SOURCE_36A_PATTERN = "4B436636A_post_phase_35_runtime_evidence_strategy_*_ready.json"

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
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "order_submit_performed",
    "paper_blocker_reduction_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_data_collection_allowed_now",
    "public_data_observation_allowed_now",
    "public_market_data_collection_performed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_policy_relaxed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
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
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "public_observation_preflight_executed",
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
    "public_data_collection_allowed_now",
    "public_data_observation_allowed_now",
    "read_only_endpoint_contract_relaxed",
    "observation_artifact_schema_relaxed",
    "execution_readiness_gate_relaxed",
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


def build_read_only_public_endpoint_contract(source_36a: Mapping[str, Any]) -> dict[str, Any]:
    endpoints = [
        {
            "contract_id": "public_exchange_info_snapshot",
            "endpoint_family": "public_exchange_metadata",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_klines_observation",
            "endpoint_family": "public_klines",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_mark_price_observation",
            "endpoint_family": "public_mark_price",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
        {
            "contract_id": "public_book_ticker_observation",
            "endpoint_family": "public_book_ticker",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "execution_now": False,
            "artifact_required": True,
        },
    ]
    payload: dict[str, Any] = {
        "contract_name": "read_only_public_endpoint_contract",
        "read_only_public_endpoint_contract_complete": True,
        "read_only_public_endpoint_contract_locked": True,
        "read_only_public_endpoint_count": len(endpoints),
        "read_only_public_endpoint_contract_items": endpoints,
        "read_only_public_endpoint_contract_status": "READ_ONLY_PUBLIC_ENDPOINT_CONTRACT_READY_NOT_EXECUTED",
        "read_only_endpoint_contract_relaxed": False,
        "public_endpoint_execution_allowed_now": False,
        "public_data_observation_allowed_now": False,
        "public_data_collection_allowed_now": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "order_submit_performed": False,
        "source_36a_public_data_observation_boundary_digest": source_36a.get("public_data_observation_boundary_digest"),
    }
    payload["read_only_public_endpoint_contract_digest"] = stable_digest(payload)
    return payload


def build_observation_artifact_schema(source_36a: Mapping[str, Any]) -> dict[str, Any]:
    schema_fields = [
        {"field": "patch_version", "required": True, "type": "string"},
        {"field": "observation_scope_id", "required": True, "type": "string"},
        {"field": "symbol", "required": True, "type": "string"},
        {"field": "timeframe", "required": False, "type": "string|null"},
        {"field": "captured_at_utc", "required": True, "type": "string"},
        {"field": "source_endpoint_family", "required": True, "type": "string"},
        {"field": "payload_digest", "required": True, "type": "sha256_hex"},
        {"field": "submit_flags", "required": True, "type": "object"},
        {"field": "validation_errors", "required": True, "type": "array"},
    ]
    payload: dict[str, Any] = {
        "schema_name": "observation_artifact_schema",
        "observation_artifact_schema_complete": True,
        "observation_artifact_schema_locked": True,
        "observation_artifact_schema_version": "1.0",
        "observation_artifact_schema_field_count": len(schema_fields),
        "observation_artifact_schema_required_field_count": sum(1 for item in schema_fields if item.get("required") is True),
        "observation_artifact_schema_fields": schema_fields,
        "observation_artifact_schema_status": "OBSERVATION_ARTIFACT_SCHEMA_READY_NOT_WRITTEN_BY_COLLECTOR",
        "observation_artifact_schema_relaxed": False,
        "observation_artifact_written": False,
        "observation_artifact_validation_performed": False,
        "runtime_evidence_collection_performed": False,
        "source_36a_runtime_evidence_collection_policy_digest": source_36a.get("runtime_evidence_collection_policy_digest"),
    }
    payload["observation_artifact_schema_digest"] = stable_digest(payload)
    return payload


def build_no_submit_execution_readiness_gate(source_36a: Mapping[str, Any]) -> dict[str, Any]:
    readiness_checks = [
        {"check_id": "source_36a_ready", "ready": True, "execution_now": False},
        {"check_id": "read_only_public_contract_locked", "ready": True, "execution_now": False},
        {"check_id": "observation_artifact_schema_locked", "ready": True, "execution_now": False},
        {"check_id": "private_api_forbidden", "ready": True, "execution_now": False},
        {"check_id": "order_submit_forbidden", "ready": True, "execution_now": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "execution_now": False},
    ]
    payload: dict[str, Any] = {
        "gate_name": "no_submit_execution_readiness_gate",
        "no_submit_execution_readiness_gate_complete": True,
        "no_submit_execution_readiness_gate_locked": True,
        "no_submit_execution_readiness_gate_status": "NO_SUBMIT_EXECUTION_READINESS_GATE_LOCKED_PREFLIGHT_ONLY",
        "execution_readiness_check_count": len(readiness_checks),
        "execution_readiness_ready_count": sum(1 for item in readiness_checks if item.get("ready") is True),
        "execution_readiness_checks": readiness_checks,
        "public_observation_execution_preflight_ready": True,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "public_observation_preflight_executed": False,
        "execution_readiness_gate_relaxed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "source_36a_paper_transition_blocker_reduction_plan_digest": source_36a.get("paper_transition_blocker_reduction_plan_digest"),
    }
    payload["no_submit_execution_readiness_gate_digest"] = stable_digest(payload)
    return payload


def _build_missing_contract_payload() -> dict[str, Any]:
    return {
        "read_only_public_endpoint_contract_complete": False,
        "read_only_public_endpoint_contract_locked": False,
        "read_only_public_endpoint_count": 0,
        "read_only_public_endpoint_contract_status": "READ_ONLY_PUBLIC_ENDPOINT_CONTRACT_NOT_READY_SOURCE_MISSING",
        "read_only_public_endpoint_contract_digest": stable_digest({"missing_source_36a": True}),
        "read_only_endpoint_contract_relaxed": False,
        "public_endpoint_execution_allowed_now": False,
    }


def _build_missing_schema_payload() -> dict[str, Any]:
    return {
        "observation_artifact_schema_complete": False,
        "observation_artifact_schema_locked": False,
        "observation_artifact_schema_field_count": 0,
        "observation_artifact_schema_required_field_count": 0,
        "observation_artifact_schema_status": "OBSERVATION_ARTIFACT_SCHEMA_NOT_READY_SOURCE_MISSING",
        "observation_artifact_schema_digest": stable_digest({"missing_source_36a": True}),
        "observation_artifact_schema_relaxed": False,
        "observation_artifact_written": False,
    }


def _build_missing_gate_payload() -> dict[str, Any]:
    return {
        "no_submit_execution_readiness_gate_complete": False,
        "no_submit_execution_readiness_gate_locked": False,
        "execution_readiness_check_count": 0,
        "execution_readiness_ready_count": 0,
        "no_submit_execution_readiness_gate_status": "NO_SUBMIT_EXECUTION_READINESS_GATE_NOT_READY_SOURCE_MISSING",
        "no_submit_execution_readiness_gate_digest": stable_digest({"missing_source_36a": True}),
        "public_observation_execution_preflight_ready": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
        "public_observation_preflight_executed": False,
        "execution_readiness_gate_relaxed": False,
    }


def evaluate_public_observation_execution_preflight(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36A_PATTERN)
    source_36a: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36a_report:{SOURCE_36A_PATTERN}")
    else:
        try:
            source_36a = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_36a_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36a, NO_SUBMIT_FALSE_FLAGS) if source_36a else []
    source_36a_complete = (
        bool(source_36a)
        and source_36a.get("status") == "READY"
        and source_36a.get("decision") == "POST_PHASE_35_RUNTIME_EVIDENCE_STRATEGY_READY_NO_SUBMIT_POLICY_BOUNDARY_LOCKED"
        and source_36a.get("phase_35_closed") is True
        and source_36a.get("phase_36_planning_only") is True
        and source_36a.get("post_phase_35_runtime_evidence_strategy_ready") is True
        and source_36a.get("runtime_evidence_collection_policy_complete") is True
        and source_36a.get("public_data_observation_boundary_locked") is True
        and source_36a.get("paper_transition_blocker_reduction_plan_complete") is True
        and source_36a.get("no_submit_phase_36a_strategy_boundary_locked") is True
        and len(source_safety_violations) == 0
    )

    contract = build_read_only_public_endpoint_contract(source_36a) if source_36a_complete else _build_missing_contract_payload()
    schema = build_observation_artifact_schema(source_36a) if source_36a_complete else _build_missing_schema_payload()
    gate = build_no_submit_execution_readiness_gate(source_36a) if source_36a_complete else _build_missing_gate_payload()

    preflight_ready = (
        source_36a_complete
        and bool(contract.get("read_only_public_endpoint_contract_complete"))
        and bool(contract.get("read_only_public_endpoint_contract_locked"))
        and bool(schema.get("observation_artifact_schema_complete"))
        and bool(schema.get("observation_artifact_schema_locked"))
        and bool(gate.get("no_submit_execution_readiness_gate_complete"))
        and bool(gate.get("no_submit_execution_readiness_gate_locked"))
        and not errors
    )

    status = "READY" if preflight_ready else "NOT_READY"
    decision = READY_DECISION if preflight_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": preflight_ready,
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
        "source_36a_complete": source_36a_complete,
        "source_36a_status": "SOURCE_36A_READY" if source_36a_complete else "SOURCE_36A_NOT_READY",
        "source_36a_report": str(source_path) if source_path else None,
        "source_36a_decision": source_36a.get("decision"),
        "source_36a_safety_violation_count": len(source_safety_violations),
        "source_36a_safety_violations": source_safety_violations,
        "source_36a_phase_35_closed": source_36a.get("phase_35_closed"),
        "source_36a_phase_36_planning_only": source_36a.get("phase_36_planning_only"),
        "source_36a_runtime_evidence_collection_policy_digest": source_36a.get("runtime_evidence_collection_policy_digest"),
        "source_36a_public_data_observation_boundary_digest": source_36a.get("public_data_observation_boundary_digest"),
        "source_36a_paper_transition_blocker_reduction_plan_digest": source_36a.get("paper_transition_blocker_reduction_plan_digest"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36a.get("phase_35_closed")) if source_36a else False,
        "phase_36_planning_only": True,
        "public_observation_execution_preflight_ready": preflight_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_READY_PLANNING_ONLY_NO_SUBMIT" if preflight_ready else "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_PREFLIGHT_ONLY_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_execution_preflight": preflight_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "read_only_public_endpoint_contract_path": None,
        "observation_artifact_schema_path": None,
        "no_submit_execution_readiness_gate_path": None,
        "report_path": None,
    }
    result.update(contract)
    result.update(schema)
    result.update(gate)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["public_observation_execution_allowed_now"] = False
    result["public_observation_execution_performed"] = False
    result["public_observation_preflight_executed"] = False
    result["read_only_endpoint_contract_relaxed"] = False
    result["observation_artifact_schema_relaxed"] = False
    result["execution_readiness_gate_relaxed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        contract_path = reports_dir / f"{PATCH_ID}_read_only_public_endpoint_contract_{stamp}.json"
        schema_path = reports_dir / f"{PATCH_ID}_observation_artifact_schema_{stamp}.json"
        gate_path = reports_dir / f"{PATCH_ID}_no_submit_execution_readiness_gate_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_execution_preflight_{stamp}_{status.lower()}.json"
        write_json(contract_path, contract)
        write_json(schema_path, schema)
        write_json(gate_path, gate)
        result["read_only_public_endpoint_contract_path"] = str(contract_path)
        result["observation_artifact_schema_path"] = str(schema_path)
        result["no_submit_execution_readiness_gate_path"] = str(gate_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write contract, schema and gate reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_execution_preflight(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
