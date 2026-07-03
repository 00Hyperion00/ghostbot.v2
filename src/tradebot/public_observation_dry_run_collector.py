from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436636C"
PATCH_VERSION = "4B.4.3.6.6.36C"
PATCH_NAME = "Public Observation Dry-Run Collector"
CHECK_NAME = "public_observation_dry_run_collector"
READY_DECISION = "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_READY_NO_SUBMIT_RUNTIME_EVIDENCE_GUARD_LOCKED"
NOT_READY_DECISION = "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.36D"
SOURCE_36B_PATTERN = "4B436636B_public_observation_execution_preflight_*_ready.json"

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
    "execution_readiness_gate_relaxed",
    "file_delete_performed",
    "file_move_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "observation_artifact_schema_relaxed",
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
    "public_data_observation_allowed_now",
    "public_endpoint_execution_allowed_now",
    "public_market_data_collection_performed",
    "public_observation_execution_allowed_now",
    "public_observation_execution_performed",
    "public_observation_preflight_executed",
    "read_only_endpoint_contract_relaxed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
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
    "public_data_collection_allowed_now",
    "public_data_observation_allowed_now",
    "public_endpoint_execution_allowed_now",
    "public_observation_execution_allowed_now",
    "read_only_public_data_fetch_adapter_relaxed",
    "observation_artifact_writer_relaxed",
    "no_submit_runtime_evidence_guard_relaxed",
    "observation_artifact_written",
    "observation_artifact_validation_performed",
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


def _source_endpoint_items(source_36b: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_items = source_36b.get("read_only_public_endpoint_contract_items")
    if isinstance(raw_items, list) and raw_items:
        normalized: list[dict[str, Any]] = []
        for item in raw_items:
            if isinstance(item, Mapping):
                normalized.append(
                    {
                        "adapter_scope_id": str(item.get("contract_id", "unknown_public_scope")),
                        "endpoint_family": str(item.get("endpoint_family", "unknown_public_endpoint")),
                        "private_api_required": False,
                        "signed_request_allowed": False,
                        "order_submit_allowed": False,
                        "network_execution_now": False,
                        "artifact_candidate_required": True,
                    }
                )
        if normalized:
            return normalized
    return [
        {
            "adapter_scope_id": "public_exchange_info_snapshot",
            "endpoint_family": "public_exchange_metadata",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "network_execution_now": False,
            "artifact_candidate_required": True,
        },
        {
            "adapter_scope_id": "public_klines_observation",
            "endpoint_family": "public_klines",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "network_execution_now": False,
            "artifact_candidate_required": True,
        },
        {
            "adapter_scope_id": "public_mark_price_observation",
            "endpoint_family": "public_mark_price",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "network_execution_now": False,
            "artifact_candidate_required": True,
        },
        {
            "adapter_scope_id": "public_book_ticker_observation",
            "endpoint_family": "public_book_ticker",
            "private_api_required": False,
            "signed_request_allowed": False,
            "order_submit_allowed": False,
            "network_execution_now": False,
            "artifact_candidate_required": True,
        },
    ]


def build_read_only_public_data_fetch_adapter(source_36b: Mapping[str, Any]) -> dict[str, Any]:
    adapter_items = _source_endpoint_items(source_36b)
    payload: dict[str, Any] = {
        "adapter_name": "read_only_public_data_fetch_adapter",
        "read_only_public_data_fetch_adapter_complete": True,
        "read_only_public_data_fetch_adapter_locked": True,
        "read_only_public_data_fetch_adapter_status": "READ_ONLY_PUBLIC_DATA_FETCH_ADAPTER_READY_NO_NETWORK_EXECUTION",
        "read_only_public_data_fetch_adapter_mode": "DRY_RUN_STUB_NO_NETWORK",
        "read_only_public_data_fetch_adapter_item_count": len(adapter_items),
        "read_only_public_data_fetch_adapter_items": adapter_items,
        "read_only_public_data_fetch_adapter_relaxed": False,
        "public_data_fetch_adapter_executable_now": False,
        "public_data_fetch_adapter_executed": False,
        "public_endpoint_execution_allowed_now": False,
        "public_observation_execution_allowed_now": False,
        "public_data_observation_allowed_now": False,
        "public_data_collection_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "order_submit_performed": False,
        "source_36b_read_only_public_endpoint_contract_digest": source_36b.get("read_only_public_endpoint_contract_digest"),
    }
    payload["read_only_public_data_fetch_adapter_digest"] = stable_digest(payload)
    return payload


def build_observation_artifact_writer(source_36b: Mapping[str, Any]) -> dict[str, Any]:
    writer_fields = source_36b.get("observation_artifact_schema_fields")
    if not isinstance(writer_fields, list):
        writer_fields = []
    candidates = [
        {
            "candidate_id": "public_exchange_info_snapshot_artifact",
            "source_scope_id": "public_exchange_info_snapshot",
            "write_now": False,
            "requires_schema_version": "1.0",
        },
        {
            "candidate_id": "public_klines_observation_artifact",
            "source_scope_id": "public_klines_observation",
            "write_now": False,
            "requires_schema_version": "1.0",
        },
        {
            "candidate_id": "public_mark_price_observation_artifact",
            "source_scope_id": "public_mark_price_observation",
            "write_now": False,
            "requires_schema_version": "1.0",
        },
        {
            "candidate_id": "public_book_ticker_observation_artifact",
            "source_scope_id": "public_book_ticker_observation",
            "write_now": False,
            "requires_schema_version": "1.0",
        },
    ]
    payload: dict[str, Any] = {
        "writer_name": "observation_artifact_writer",
        "observation_artifact_writer_complete": True,
        "observation_artifact_writer_locked": True,
        "observation_artifact_writer_status": "OBSERVATION_ARTIFACT_WRITER_READY_NOT_WRITING_BY_DEFAULT",
        "observation_artifact_writer_mode": "SCHEMA_BOUND_DRY_RUN_NO_PAYLOAD_CAPTURE",
        "observation_artifact_writer_relaxed": False,
        "observation_artifact_writer_schema_version": str(source_36b.get("observation_artifact_schema_version", "1.0")),
        "observation_artifact_writer_schema_field_count": len(writer_fields),
        "observation_artifact_candidate_count": len(candidates),
        "observation_artifact_candidates": candidates,
        "observation_artifact_write_allowed_now": False,
        "observation_artifact_written": False,
        "observation_artifact_validation_performed": False,
        "observation_payload_captured": False,
        "runtime_evidence_artifact_written": False,
        "source_36b_observation_artifact_schema_digest": source_36b.get("observation_artifact_schema_digest"),
    }
    payload["observation_artifact_writer_digest"] = stable_digest(payload)
    return payload


def build_no_submit_runtime_evidence_guard(source_36b: Mapping[str, Any]) -> dict[str, Any]:
    guard_checks = [
        {"check_id": "source_36b_ready", "ready": True, "execution_now": False},
        {"check_id": "fetch_adapter_no_network", "ready": True, "execution_now": False},
        {"check_id": "artifact_writer_not_writing", "ready": True, "execution_now": False},
        {"check_id": "private_api_forbidden", "ready": True, "execution_now": False},
        {"check_id": "order_submit_forbidden", "ready": True, "execution_now": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "execution_now": False},
        {"check_id": "runtime_probe_separated", "ready": True, "execution_now": False},
    ]
    payload: dict[str, Any] = {
        "guard_name": "no_submit_runtime_evidence_guard",
        "no_submit_runtime_evidence_guard_complete": True,
        "no_submit_runtime_evidence_guard_locked": True,
        "no_submit_runtime_evidence_guard_status": "NO_SUBMIT_RUNTIME_EVIDENCE_GUARD_LOCKED_DRY_RUN_COLLECTOR_ONLY",
        "no_submit_runtime_evidence_guard_relaxed": False,
        "runtime_evidence_guard_check_count": len(guard_checks),
        "runtime_evidence_guard_ready_count": sum(1 for item in guard_checks if item.get("ready") is True),
        "runtime_evidence_guard_checks": guard_checks,
        "public_observation_dry_run_collector_ready": True,
        "public_observation_dry_run_collector_executable_now": False,
        "public_observation_dry_run_collector_executed": False,
        "public_observation_execution_allowed_now": False,
        "public_observation_execution_performed": False,
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
        "source_36b_no_submit_execution_readiness_gate_digest": source_36b.get("no_submit_execution_readiness_gate_digest"),
    }
    payload["no_submit_runtime_evidence_guard_digest"] = stable_digest(payload)
    return payload


def _build_missing_adapter_payload() -> dict[str, Any]:
    return {
        "read_only_public_data_fetch_adapter_complete": False,
        "read_only_public_data_fetch_adapter_locked": False,
        "read_only_public_data_fetch_adapter_status": "READ_ONLY_PUBLIC_DATA_FETCH_ADAPTER_NOT_READY_SOURCE_MISSING",
        "read_only_public_data_fetch_adapter_digest": stable_digest({"missing_source_36b": True}),
        "read_only_public_data_fetch_adapter_item_count": 0,
        "read_only_public_data_fetch_adapter_relaxed": False,
        "public_data_fetch_adapter_executable_now": False,
        "public_data_fetch_adapter_executed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
    }


def _build_missing_writer_payload() -> dict[str, Any]:
    return {
        "observation_artifact_writer_complete": False,
        "observation_artifact_writer_locked": False,
        "observation_artifact_writer_status": "OBSERVATION_ARTIFACT_WRITER_NOT_READY_SOURCE_MISSING",
        "observation_artifact_writer_digest": stable_digest({"missing_source_36b": True}),
        "observation_artifact_writer_relaxed": False,
        "observation_artifact_candidate_count": 0,
        "observation_artifact_write_allowed_now": False,
        "observation_artifact_written": False,
        "observation_artifact_validation_performed": False,
        "observation_payload_captured": False,
        "runtime_evidence_artifact_written": False,
    }


def _build_missing_guard_payload() -> dict[str, Any]:
    return {
        "no_submit_runtime_evidence_guard_complete": False,
        "no_submit_runtime_evidence_guard_locked": False,
        "no_submit_runtime_evidence_guard_status": "NO_SUBMIT_RUNTIME_EVIDENCE_GUARD_NOT_READY_SOURCE_MISSING",
        "no_submit_runtime_evidence_guard_digest": stable_digest({"missing_source_36b": True}),
        "no_submit_runtime_evidence_guard_relaxed": False,
        "runtime_evidence_guard_check_count": 0,
        "runtime_evidence_guard_ready_count": 0,
        "public_observation_dry_run_collector_ready": False,
        "public_observation_dry_run_collector_executable_now": False,
        "public_observation_dry_run_collector_executed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
    }


def evaluate_public_observation_dry_run_collector(
    repo_root: Path,
    reports_dir: Path,
    *,
    write_reports: bool = False,
) -> dict[str, Any]:
    reports_dir = reports_dir.resolve()
    repo_root = repo_root.resolve()
    errors: list[str] = []

    source_path = latest_report(reports_dir, SOURCE_36B_PATTERN)
    source_36b: dict[str, Any] = {}
    if source_path is None:
        errors.append(f"missing_source_36b_report:{SOURCE_36B_PATTERN}")
    else:
        try:
            source_36b = load_json(source_path)
        except Exception as exc:  # pragma: no cover - defensive CLI protection
            errors.append(f"invalid_source_36b_report:{source_path}:{exc}")

    git_state = read_git_state(repo_root)
    source_safety_violations = truthy_violations(source_36b, NO_SUBMIT_FALSE_FLAGS) if source_36b else []
    source_36b_complete = (
        bool(source_36b)
        and source_36b.get("status") == "READY"
        and source_36b.get("decision") == "PUBLIC_OBSERVATION_EXECUTION_PREFLIGHT_READY_NO_SUBMIT_EXECUTION_READINESS_GATE_LOCKED"
        and source_36b.get("phase_35_closed") is True
        and source_36b.get("phase_36_planning_only") is True
        and source_36b.get("source_36a_complete") is True
        and source_36b.get("read_only_public_endpoint_contract_complete") is True
        and source_36b.get("read_only_public_endpoint_contract_locked") is True
        and source_36b.get("observation_artifact_schema_complete") is True
        and source_36b.get("observation_artifact_schema_locked") is True
        and source_36b.get("no_submit_execution_readiness_gate_complete") is True
        and source_36b.get("no_submit_execution_readiness_gate_locked") is True
        and source_36b.get("public_observation_execution_preflight_ready") is True
        and len(source_safety_violations) == 0
    )

    adapter = build_read_only_public_data_fetch_adapter(source_36b) if source_36b_complete else _build_missing_adapter_payload()
    writer = build_observation_artifact_writer(source_36b) if source_36b_complete else _build_missing_writer_payload()
    guard = build_no_submit_runtime_evidence_guard(source_36b) if source_36b_complete else _build_missing_guard_payload()

    collector_ready = (
        source_36b_complete
        and bool(adapter.get("read_only_public_data_fetch_adapter_complete"))
        and bool(adapter.get("read_only_public_data_fetch_adapter_locked"))
        and bool(writer.get("observation_artifact_writer_complete"))
        and bool(writer.get("observation_artifact_writer_locked"))
        and bool(guard.get("no_submit_runtime_evidence_guard_complete"))
        and bool(guard.get("no_submit_runtime_evidence_guard_locked"))
        and not errors
    )

    status = "READY" if collector_ready else "NOT_READY"
    decision = READY_DECISION if collector_ready else NOT_READY_DECISION
    stamp = utc_stamp()

    result: dict[str, Any] = {
        "ok": collector_ready,
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
        "source_36b_complete": source_36b_complete,
        "source_36b_status": "SOURCE_36B_READY" if source_36b_complete else "SOURCE_36B_NOT_READY",
        "source_36b_report": str(source_path) if source_path else None,
        "source_36b_decision": source_36b.get("decision"),
        "source_36b_safety_violation_count": len(source_safety_violations),
        "source_36b_safety_violations": source_safety_violations,
        "source_36b_phase_35_closed": source_36b.get("phase_35_closed"),
        "source_36b_phase_36_planning_only": source_36b.get("phase_36_planning_only"),
        "source_36b_read_only_public_endpoint_contract_digest": source_36b.get("read_only_public_endpoint_contract_digest"),
        "source_36b_observation_artifact_schema_digest": source_36b.get("observation_artifact_schema_digest"),
        "source_36b_no_submit_execution_readiness_gate_digest": source_36b.get("no_submit_execution_readiness_gate_digest"),
        "source_36b_execution_readiness_ready_count": source_36b.get("execution_readiness_ready_count"),
        "phase_34_closed": True,
        "phase_35_closed": bool(source_36b.get("phase_35_closed")) if source_36b else False,
        "phase_36_planning_only": True,
        "public_observation_dry_run_collector_ready": collector_ready,
        "runtime_readiness_status": "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_READY_PLANNING_ONLY_NO_SUBMIT" if collector_ready else "PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_NOT_READY_NO_SUBMIT",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_OBSERVATION_DRY_RUN_COLLECTOR_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "accepted_for_public_observation_dry_run_collector": collector_ready,
        "simulated_approval_performed": False,
        "approval_performed": False,
        "read_only_public_data_fetch_adapter_path": None,
        "observation_artifact_writer_path": None,
        "no_submit_runtime_evidence_guard_path": None,
        "report_path": None,
    }
    result.update(adapter)
    result.update(writer)
    result.update(guard)

    for flag in FINAL_FALSE_FLAGS:
        result[flag] = False
    result["paper_transition_blocked"] = True
    result["paper_transition_ready"] = False
    result["paper_transition_unblocked"] = False
    result["paper_transition_approval_performed"] = False
    result["paper_environment_enabled"] = False
    result["live_environment_enabled"] = False
    result["public_observation_dry_run_collector_executable_now"] = False
    result["public_observation_dry_run_collector_executed"] = False
    result["public_data_fetch_adapter_executable_now"] = False
    result["public_data_fetch_adapter_executed"] = False
    result["network_request_performed"] = False
    result["http_request_performed"] = False
    result["signed_request_performed"] = False
    result["observation_artifact_write_allowed_now"] = False
    result["observation_artifact_written"] = False
    result["observation_artifact_validation_performed"] = False
    result["runtime_evidence_artifact_written"] = False
    result["read_only_public_data_fetch_adapter_relaxed"] = False
    result["observation_artifact_writer_relaxed"] = False
    result["no_submit_runtime_evidence_guard_relaxed"] = False

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        adapter_path = reports_dir / f"{PATCH_ID}_read_only_public_data_fetch_adapter_{stamp}.json"
        writer_path = reports_dir / f"{PATCH_ID}_observation_artifact_writer_{stamp}.json"
        guard_path = reports_dir / f"{PATCH_ID}_no_submit_runtime_evidence_guard_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_observation_dry_run_collector_{stamp}_{status.lower()}.json"
        write_json(adapter_path, adapter)
        write_json(writer_path, writer)
        write_json(guard_path, guard)
        result["read_only_public_data_fetch_adapter_path"] = str(adapter_path)
        result["observation_artifact_writer_path"] = str(writer_path)
        result["no_submit_runtime_evidence_guard_path"] = str(guard_path)
        result["report_path"] = str(report_path)
        write_json(report_path, result)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Recovery reports directory.")
    parser.add_argument("--once-json", action="store_true", help="Print exactly one JSON object.")
    parser.add_argument("--write-reports", action="store_true", help="Write adapter, writer and guard reports.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = evaluate_public_observation_dry_run_collector(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=bool(args.write_reports),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
