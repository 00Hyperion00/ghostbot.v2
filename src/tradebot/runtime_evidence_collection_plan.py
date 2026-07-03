from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PATCH_ID = "4B436635C"
PATCH_VERSION = "4B.4.3.6.6.35C"
PATCH_NAME = "Runtime Evidence Collection Plan"
CHECK_NAME = "runtime_evidence_collection_plan"
READY_DECISION = "RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED"
NOT_READY_DECISION = "RUNTIME_EVIDENCE_COLLECTION_PLAN_NOT_READY"
SOURCE_DECISION = "RUNTIME_READINESS_EVIDENCE_EXPANSION_READY_NO_SUBMIT_EVIDENCE_PACK_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.35D"

FALSE_SAFETY_FIELDS: tuple[str, ...] = (
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
    "archive_execution_allowed",
    "archive_move_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "destructive_cleanup_performed",
    "deduplication_action_performed",
    "approval_performed",
    "simulated_approval_performed",
    "submit_boundary_relaxed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "runtime_readiness_unlock_performed",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_environment_enabled",
    "live_environment_enabled",
    "runtime_evidence_collection_performed",
    "collection_runbook_executed",
    "evidence_collection_started",
    "public_market_data_collection_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "runtime_health_probe_performed",
)

EVIDENCE_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "source_id": "runtime_health_status_snapshot",
        "domain": "runtime_bootstrap",
        "source_type": "local_api_health_status",
        "collection_mode": "future_no_submit_read_only",
        "current_state": "registered_not_collected",
        "requires_exchange_submit": False,
        "requires_network_submit": False,
        "requires_private_api": False,
        "linked_blocker": "RUNTIME_SERVICE_BOOTSTRAP_EVIDENCE_REQUIRED",
    },
    {
        "source_id": "operator_cockpit_status_contract_replay",
        "domain": "operator_cockpit_contract",
        "source_type": "offline_status_contract_replay",
        "collection_mode": "future_no_submit_replay_only",
        "current_state": "registered_not_collected",
        "requires_exchange_submit": False,
        "requires_network_submit": False,
        "requires_private_api": False,
        "linked_blocker": "OPERATOR_COCKPIT_STATUS_CONTRACT_EVIDENCE_REQUIRED",
    },
    {
        "source_id": "public_market_data_observation",
        "domain": "market_data_public_only",
        "source_type": "public_market_data_snapshot",
        "collection_mode": "future_public_read_only_observation",
        "current_state": "registered_not_collected",
        "requires_exchange_submit": False,
        "requires_network_submit": False,
        "requires_private_api": False,
        "linked_blocker": "PUBLIC_MARKET_DATA_RUNTIME_EVIDENCE_REQUIRED",
    },
    {
        "source_id": "runtime_risk_boundary_assertions",
        "domain": "risk_boundary_assertions",
        "source_type": "local_assertion_report",
        "collection_mode": "future_no_submit_assertion_only",
        "current_state": "registered_not_collected",
        "requires_exchange_submit": False,
        "requires_network_submit": False,
        "requires_private_api": False,
        "linked_blocker": "RISK_BOUNDARY_RUNTIME_ASSERTIONS_REQUIRED",
    },
    {
        "source_id": "operator_paper_transition_governance",
        "domain": "paper_transition_governance",
        "source_type": "operator_approval_ledger_future",
        "collection_mode": "future_governance_only",
        "current_state": "registered_not_collected",
        "requires_exchange_submit": False,
        "requires_network_submit": False,
        "requires_private_api": False,
        "linked_blocker": "PAPER_TRANSITION_OPERATOR_GATE_REQUIRED",
    },
)


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def bool_false(value: Any) -> bool:
    return value is False or value in (0, "false", "False", "FALSE", None)


def safety_violations(source: Mapping[str, Any], fields: Iterable[str] = FALSE_SAFETY_FIELDS) -> list[str]:
    return [field for field in fields if not bool_false(source.get(field, False))]


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = sorted(
        reports_dir.glob("4B436635B_runtime_readiness_evidence_expansion_*_ready.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def git_output(args: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return None
    return completed.stdout.strip()


def git_context(root: Path) -> dict[str, Any]:
    branch = git_output(["rev-parse", "--abbrev-ref", "HEAD"], root)
    head = git_output(["rev-parse", "--short", "HEAD"], root)
    tags = git_output(["tag", "--list", "4B.4.3.6.6.35*"], root)
    return {
        "git_available": branch is not None and head is not None,
        "git_branch": branch,
        "git_head_short": head,
        "phase_35_tag_count_observed": len([line for line in (tags or "").splitlines() if line.strip()]),
    }


@dataclass(frozen=True)
class CollectionPlanArtifacts:
    evidence_source_registry: dict[str, Any]
    collection_runbook_matrix: dict[str, Any]
    no_submit_collection_boundary: dict[str, Any]


def build_evidence_source_registry(source: Mapping[str, Any]) -> dict[str, Any]:
    rows = [dict(row) for row in EVIDENCE_SOURCES]
    registry: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "registry_name": "evidence_source_registry",
        "source_35b_report": source.get("source_report_path"),
        "source_35b_readiness_blocker_detail_count": source.get("readiness_blocker_detail_count"),
        "source_35b_runtime_evidence_pack_digest": source.get("no_submit_runtime_evidence_pack_digest"),
        "evidence_sources": rows,
        "evidence_source_registry_complete": True,
        "evidence_source_count": len(rows),
        "evidence_source_registry_status": "EVIDENCE_SOURCE_REGISTRY_READY_COLLECTION_NOT_STARTED",
        "evidence_collection_started": False,
        "runtime_evidence_collection_performed": False,
        "private_api_access_allowed": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
    }
    registry["evidence_source_registry_digest"] = sha256_json(registry)
    return registry


def build_collection_runbook_matrix(source: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    runbooks: list[dict[str, Any]] = []
    for index, row in enumerate(registry.get("evidence_sources", []), start=1):
        if not isinstance(row, Mapping):
            continue
        runbooks.append(
            {
                "sequence": index,
                "runbook_id": f"collect_{row.get('source_id')}",
                "source_id": row.get("source_id"),
                "domain": row.get("domain"),
                "mode": row.get("collection_mode"),
                "execution_status": "PLANNED_NOT_EXECUTED",
                "boundary": "NO_SUBMIT_COLLECTION_BOUNDARY",
                "requires_operator_review_before_execution": True,
                "requires_exchange_submit": False,
                "requires_network_submit": False,
                "requires_private_api": False,
            }
        )
    matrix: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "matrix_name": "collection_runbook_matrix",
        "source_35b_report": source.get("source_report_path"),
        "evidence_source_registry_digest": registry.get("evidence_source_registry_digest"),
        "collection_runbooks": runbooks,
        "collection_runbook_matrix_complete": True,
        "collection_runbook_count": len(runbooks),
        "collection_runbook_executable_now": False,
        "collection_runbook_executed": False,
        "collection_runbook_status": "COLLECTION_RUNBOOK_MATRIX_READY_NOT_EXECUTED_NO_SUBMIT",
        "runtime_evidence_collection_performed": False,
        "public_market_data_collection_performed": False,
        "paper_transition_blocked": True,
    }
    matrix["collection_runbook_matrix_digest"] = sha256_json(matrix)
    return matrix


def build_no_submit_collection_boundary(source: Mapping[str, Any], registry: Mapping[str, Any], matrix: Mapping[str, Any]) -> dict[str, Any]:
    boundary: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "boundary_name": "no_submit_collection_boundary",
        "source_35b_report": source.get("source_report_path"),
        "evidence_source_registry_digest": registry.get("evidence_source_registry_digest"),
        "collection_runbook_matrix_digest": matrix.get("collection_runbook_matrix_digest"),
        "no_submit_collection_boundary_complete": True,
        "no_submit_collection_boundary_locked": True,
        "no_submit_collection_boundary_status": "NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED_COLLECTION_NOT_STARTED",
        "runtime_evidence_collection_allowed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "collection_runbook_executed": False,
        "public_market_data_collection_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "paper_transition_blocked": True,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "order_submit_performed": False,
    }
    boundary["no_submit_collection_boundary_digest"] = sha256_json(boundary)
    return boundary


def build_artifacts(source: Mapping[str, Any]) -> CollectionPlanArtifacts:
    registry = build_evidence_source_registry(source)
    matrix = build_collection_runbook_matrix(source, registry)
    boundary = build_no_submit_collection_boundary(source, registry, matrix)
    return CollectionPlanArtifacts(
        evidence_source_registry=registry,
        collection_runbook_matrix=matrix,
        no_submit_collection_boundary=boundary,
    )


def source_35b_is_complete(source: Mapping[str, Any], source_safety_violations: list[str]) -> bool:
    return bool(
        source
        and source.get("status") == "READY"
        and source.get("decision") == SOURCE_DECISION
        and source.get("source_35a_complete") is True
        and source.get("phase_34_closed") is True
        and source.get("phase_35_planning_only") is True
        and source.get("readiness_blocker_detail_ledger_complete") is True
        and source.get("paper_transition_criteria_matrix_complete") is True
        and source.get("no_submit_runtime_evidence_pack_complete") is True
        and source.get("runtime_readiness_evidence_expanded") is True
        and source.get("paper_transition_blocked") is True
        and bool_false(source.get("paper_transition_unblocked", False))
        and bool_false(source.get("runtime_evidence_collection_performed", False))
        and len(source_safety_violations) == 0
    )


def evaluate(root: Path, reports_dir: Path, write_reports: bool = False) -> dict[str, Any]:
    root = root.resolve()
    reports_dir = reports_dir if reports_dir.is_absolute() else (root / reports_dir)
    report_ts = utc_now_compact()
    source_path = find_latest_source_report(reports_dir)
    errors: list[str] = []
    source: dict[str, Any] = {}

    if source_path is None:
        errors.append("SOURCE_35B_READY_REPORT_MISSING")
    else:
        try:
            source = read_json(source_path)
            source["source_report_path"] = str(source_path)
        except Exception as exc:
            errors.append(f"SOURCE_35B_REPORT_READ_FAILED:{exc}")

    source_safety_violations = safety_violations(source) if source else []
    source_35b_complete = source_35b_is_complete(source, source_safety_violations)
    if source and not source_35b_complete:
        errors.append("SOURCE_35B_NOT_READY_OR_SAFETY_VIOLATION")

    artifacts = build_artifacts(source) if source else None
    evidence_source_registry_complete = bool(artifacts and artifacts.evidence_source_registry.get("evidence_source_registry_complete"))
    collection_runbook_matrix_complete = bool(artifacts and artifacts.collection_runbook_matrix.get("collection_runbook_matrix_complete"))
    no_submit_collection_boundary_complete = bool(artifacts and artifacts.no_submit_collection_boundary.get("no_submit_collection_boundary_complete"))

    status_ready = bool(
        source_35b_complete
        and evidence_source_registry_complete
        and collection_runbook_matrix_complete
        and no_submit_collection_boundary_complete
        and not errors
    )

    evidence_source_registry_path: str | None = None
    collection_runbook_matrix_path: str | None = None
    no_submit_collection_boundary_path: str | None = None

    if write_reports and artifacts is not None:
        registry_file = reports_dir / f"{PATCH_ID}_evidence_source_registry_{report_ts}.json"
        runbook_file = reports_dir / f"{PATCH_ID}_collection_runbook_matrix_{report_ts}.json"
        boundary_file = reports_dir / f"{PATCH_ID}_no_submit_collection_boundary_{report_ts}.json"
        write_json(registry_file, artifacts.evidence_source_registry)
        write_json(runbook_file, artifacts.collection_runbook_matrix)
        write_json(boundary_file, artifacts.no_submit_collection_boundary)
        evidence_source_registry_path = str(registry_file)
        collection_runbook_matrix_path = str(runbook_file)
        no_submit_collection_boundary_path = str(boundary_file)

    false_field_values = {field: False for field in FALSE_SAFETY_FIELDS}
    result: dict[str, Any] = {
        "ok": status_ready,
        "status": "READY" if status_ready else "NOT_READY",
        "decision": READY_DECISION if status_ready else NOT_READY_DECISION,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "source_35b_complete": source_35b_complete,
        "source_35b_status": "SOURCE_35B_READY" if source_35b_complete else "SOURCE_35B_NOT_READY",
        "source_35b_decision": source.get("decision") if source else None,
        "source_35b_report": str(source_path) if source_path else None,
        "source_35b_safety_violation_count": len(source_safety_violations),
        "source_35b_safety_violations": source_safety_violations,
        "source_35b_readiness_blocker_detail_count": source.get("readiness_blocker_detail_count"),
        "source_35b_paper_transition_criteria_open_count": source.get("paper_transition_criteria_open_count"),
        "source_35b_runtime_evidence_pack_item_count": source.get("runtime_evidence_pack_item_count"),
        "phase_34_closed": bool(source.get("phase_34_closed", False)),
        "phase_35_planning_only": True,
        "evidence_source_registry_complete": evidence_source_registry_complete,
        "evidence_source_registry_status": artifacts.evidence_source_registry.get("evidence_source_registry_status") if artifacts else None,
        "evidence_source_count": artifacts.evidence_source_registry.get("evidence_source_count") if artifacts else 0,
        "evidence_source_registry_digest": artifacts.evidence_source_registry.get("evidence_source_registry_digest") if artifacts else None,
        "evidence_source_registry_path": evidence_source_registry_path,
        "collection_runbook_matrix_complete": collection_runbook_matrix_complete,
        "collection_runbook_status": artifacts.collection_runbook_matrix.get("collection_runbook_status") if artifacts else None,
        "collection_runbook_count": artifacts.collection_runbook_matrix.get("collection_runbook_count") if artifacts else 0,
        "collection_runbook_executable_now": False,
        "collection_runbook_matrix_digest": artifacts.collection_runbook_matrix.get("collection_runbook_matrix_digest") if artifacts else None,
        "collection_runbook_matrix_path": collection_runbook_matrix_path,
        "no_submit_collection_boundary_complete": no_submit_collection_boundary_complete,
        "no_submit_collection_boundary_locked": bool(artifacts and artifacts.no_submit_collection_boundary.get("no_submit_collection_boundary_locked")),
        "no_submit_collection_boundary_status": artifacts.no_submit_collection_boundary.get("no_submit_collection_boundary_status") if artifacts else None,
        "no_submit_collection_boundary_digest": artifacts.no_submit_collection_boundary.get("no_submit_collection_boundary_digest") if artifacts else None,
        "no_submit_collection_boundary_path": no_submit_collection_boundary_path,
        "accepted_for_runtime_evidence_collection_plan": status_ready,
        "runtime_evidence_collection_plan_ready": status_ready,
        "runtime_readiness_status": "RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_PLANNING_ONLY_NO_SUBMIT" if status_ready else "RUNTIME_EVIDENCE_COLLECTION_PLAN_NOT_READY",
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_COLLECTION_PLAN_ONLY_NO_SUBMIT",
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "runtime_readiness_ready_count": 0,
        "runtime_readiness_blocker_count": source.get("runtime_readiness_blocker_count", source.get("readiness_blocker_detail_count", 0)),
        "next_phase": NEXT_PHASE,
        "errors": errors,
        "report_path": None,
        **false_field_values,
        **git_context(root),
    }

    if write_reports:
        status_suffix = "ready" if status_ready else "not_ready"
        result_file = reports_dir / f"{PATCH_ID}_runtime_evidence_collection_plan_{report_ts}_{status_suffix}.json"
        result["report_path"] = str(result_file)
        write_json(result_file, result)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    result = evaluate(Path(args.root), Path(args.reports_dir), write_reports=args.write_reports)
    if args.once_json or True:
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
