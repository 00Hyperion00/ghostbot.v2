from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PATCH_ID = "4B436635A"
PATCH_VERSION = "4B.4.3.6.6.35A"
PATCH_NAME = "Post-Governance Runtime Readiness Planning"
CHECK_NAME = "post_governance_runtime_readiness_planning"
READY_DECISION = "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_READY_NO_SUBMIT_BOUNDARY_CARRIED_FORWARD"
NOT_READY_DECISION = "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_NOT_READY"
SOURCE_DECISION = "POST_CLOSURE_TAG_AUDIT_READY_NO_SUBMIT_PHASE_34_FINAL_SEALED"
NEXT_PHASE = "4B.4.3.6.6.35B"

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
)

CARRY_FORWARD_FALSE_FIELDS: tuple[str, ...] = FALSE_SAFETY_FIELDS + (
    "runtime_readiness_unlock_performed",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_environment_enabled",
    "live_environment_enabled",
)

RUNTIME_READINESS_ROWS: tuple[dict[str, Any], ...] = (
    {
        "area": "runtime_service_bootstrap",
        "required_evidence": "health/status evidence pack under no-submit mode",
        "current_state": "planning_only",
        "target_state": "evidence_required_before_paper_candidate",
        "ready": False,
        "blocking_code": "RUNTIME_SERVICE_BOOTSTRAP_EVIDENCE_REQUIRED",
    },
    {
        "area": "operator_cockpit_status_contract",
        "required_evidence": "stable API/status contract replay under no-submit mode",
        "current_state": "planning_only",
        "target_state": "contract_replay_required_before_paper_candidate",
        "ready": False,
        "blocking_code": "OPERATOR_COCKPIT_STATUS_CONTRACT_EVIDENCE_REQUIRED",
    },
    {
        "area": "market_data_public_only_runtime",
        "required_evidence": "public market-data ingestion evidence with exchange submit disabled",
        "current_state": "planning_only",
        "target_state": "public_data_observation_required",
        "ready": False,
        "blocking_code": "PUBLIC_MARKET_DATA_RUNTIME_EVIDENCE_REQUIRED",
    },
    {
        "area": "risk_boundary_runtime_assertions",
        "required_evidence": "runtime assertions showing all submit paths locked",
        "current_state": "boundary_carried_forward",
        "target_state": "assertion_evidence_required",
        "ready": False,
        "blocking_code": "RISK_BOUNDARY_RUNTIME_ASSERTIONS_REQUIRED",
    },
    {
        "area": "paper_transition_controls",
        "required_evidence": "separate operator-approved future paper transition gate",
        "current_state": "blocked",
        "target_state": "future_operator_gate_required",
        "ready": False,
        "blocking_code": "PAPER_TRANSITION_OPERATOR_GATE_REQUIRED",
    },
)

PAPER_TRANSITION_BLOCKERS: tuple[dict[str, Any], ...] = (
    {
        "code": "PAPER_TRANSITION_BLOCKED_BY_NO_RUNTIME_READINESS_EVIDENCE",
        "severity": "BLOCKER",
        "owner": "operator_governance",
        "resolution_phase": "future_35x_runtime_readiness_evidence",
    },
    {
        "code": "PAPER_TRANSITION_BLOCKED_BY_NO_OPERATOR_PAPER_APPROVAL",
        "severity": "BLOCKER",
        "owner": "operator_governance",
        "resolution_phase": "future_operator_approval_gate",
    },
    {
        "code": "PAPER_TRANSITION_BLOCKED_BY_NO_SUBMIT_BOUNDARY_CARRY_FORWARD",
        "severity": "BLOCKER",
        "owner": "risk_management",
        "resolution_phase": "future_no_submit_boundary_reassessment",
    },
    {
        "code": "PAPER_TRANSITION_BLOCKED_BY_NO_PAPER_ENVIRONMENT_ENABLEMENT",
        "severity": "BLOCKER",
        "owner": "runtime_operations",
        "resolution_phase": "future_paper_environment_enablement_gate",
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
        reports_dir.glob("4B436634I_post_closure_tag_audit_*_ready.json"),
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
    tags = git_output(["tag", "--list", "4B.4.3.6.6.34*"], root)
    return {
        "git_available": branch is not None and head is not None,
        "git_branch": branch,
        "git_head_short": head,
        "phase_34_tag_count_observed": len([line for line in (tags or "").splitlines() if line.strip()]),
    }


@dataclass(frozen=True)
class PlanningArtifacts:
    runtime_matrix: dict[str, Any]
    blocker_ledger: dict[str, Any]
    boundary_carry_forward: dict[str, Any]


def build_runtime_matrix(source: Mapping[str, Any]) -> dict[str, Any]:
    rows = [dict(row) for row in RUNTIME_READINESS_ROWS]
    ready_count = sum(1 for row in rows if row.get("ready") is True)
    blocker_count = sum(1 for row in rows if row.get("ready") is not True)
    matrix: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "matrix_name": "no_submit_runtime_readiness_matrix",
        "source_34i_report": source.get("source_report_path"),
        "phase_34_final_seal_digest": source.get("phase_34_final_seal_digest"),
        "runtime_readiness_matrix_rows": rows,
        "runtime_readiness_ready_count": ready_count,
        "runtime_readiness_blocker_count": blocker_count,
        "runtime_readiness_status": "RUNTIME_READINESS_PLANNING_ONLY_PAPER_BLOCKED",
        "no_submit_runtime_readiness_matrix_complete": True,
        "approved_for_paper_transition": False,
        "paper_transition_unblocked": False,
        "matrix_is_planning_only": True,
    }
    matrix["runtime_readiness_matrix_digest"] = sha256_json(matrix)
    return matrix


def build_blocker_ledger(source: Mapping[str, Any]) -> dict[str, Any]:
    blockers = [dict(row) for row in PAPER_TRANSITION_BLOCKERS]
    ledger: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "paper_transition_blocker_ledger",
        "source_34i_report": source.get("source_report_path"),
        "paper_transition_blockers": blockers,
        "paper_transition_blocker_count": len(blockers),
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PLANNING_ONLY",
        "paper_transition_blocker_ledger_complete": True,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
    }
    ledger["paper_transition_blocker_ledger_digest"] = sha256_json(ledger)
    return ledger


def build_boundary_carry_forward(source: Mapping[str, Any]) -> dict[str, Any]:
    carried_fields = {field: False for field in CARRY_FORWARD_FALSE_FIELDS}
    boundary: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "safety_boundary_carry_forward",
        "source_34i_report": source.get("source_report_path"),
        "source_34i_decision": source.get("decision"),
        "source_34i_safety_violation_count": len(safety_violations(source)),
        "source_34i_safety_violations": safety_violations(source),
        "safety_boundary_carry_forward_complete": True,
        "safety_boundary_status": "NO_SUBMIT_SAFETY_BOUNDARY_CARRIED_FORWARD",
        "boundary_carried_forward_from_phase_34": True,
        "phase_35_planning_only": True,
        **carried_fields,
    }
    boundary["safety_boundary_carry_forward_digest"] = sha256_json(boundary)
    return boundary


def build_artifacts(source: Mapping[str, Any]) -> PlanningArtifacts:
    return PlanningArtifacts(
        runtime_matrix=build_runtime_matrix(source),
        blocker_ledger=build_blocker_ledger(source),
        boundary_carry_forward=build_boundary_carry_forward(source),
    )


def evaluate(root: Path, reports_dir: Path, write_reports: bool = False) -> dict[str, Any]:
    root = root.resolve()
    reports_dir = reports_dir if reports_dir.is_absolute() else (root / reports_dir)
    report_ts = utc_now_compact()
    source_path = find_latest_source_report(reports_dir)
    errors: list[str] = []
    source: dict[str, Any] = {}

    if source_path is None:
        errors.append("SOURCE_34I_READY_REPORT_MISSING")
    else:
        try:
            source = read_json(source_path)
            source["source_report_path"] = str(source_path)
        except Exception as exc:
            errors.append(f"SOURCE_34I_REPORT_READ_FAILED:{exc}")

    source_safety_violations = safety_violations(source) if source else []
    source_34i_complete = bool(
        source
        and source.get("status") == "READY"
        and source.get("decision") == SOURCE_DECISION
        and source.get("source_34h_complete") is True
        and source.get("phase_34h_tag_present") is True
        and int(source.get("missing_tag_count", 999999)) == 0
        and source.get("no_submit_phase_34_final_sealed") is True
        and source.get("phase_34_closed") is True
        and source.get("accepted_for_phase_34_final_seal") is True
        and len(source_safety_violations) == 0
    )
    if source and not source_34i_complete:
        errors.append("SOURCE_34I_NOT_READY_OR_SAFETY_VIOLATION")

    artifacts = build_artifacts(source) if source else None
    no_submit_runtime_readiness_matrix_complete = bool(artifacts and artifacts.runtime_matrix.get("no_submit_runtime_readiness_matrix_complete"))
    paper_transition_blocker_ledger_complete = bool(artifacts and artifacts.blocker_ledger.get("paper_transition_blocker_ledger_complete"))
    safety_boundary_carry_forward_complete = bool(artifacts and artifacts.boundary_carry_forward.get("safety_boundary_carry_forward_complete"))

    false_field_values = {field: False for field in CARRY_FORWARD_FALSE_FIELDS}
    status_ready = bool(
        source_34i_complete
        and no_submit_runtime_readiness_matrix_complete
        and paper_transition_blocker_ledger_complete
        and safety_boundary_carry_forward_complete
        and not errors
    )

    runtime_matrix_path: str | None = None
    blocker_ledger_path: str | None = None
    boundary_carry_forward_path: str | None = None
    report_path: str | None = None

    if write_reports and artifacts is not None:
        runtime_matrix_file = reports_dir / f"{PATCH_ID}_no_submit_runtime_readiness_matrix_{report_ts}.json"
        blocker_ledger_file = reports_dir / f"{PATCH_ID}_paper_transition_blocker_ledger_{report_ts}.json"
        boundary_file = reports_dir / f"{PATCH_ID}_safety_boundary_carry_forward_{report_ts}.json"
        write_json(runtime_matrix_file, artifacts.runtime_matrix)
        write_json(blocker_ledger_file, artifacts.blocker_ledger)
        write_json(boundary_file, artifacts.boundary_carry_forward)
        runtime_matrix_path = str(runtime_matrix_file)
        blocker_ledger_path = str(blocker_ledger_file)
        boundary_carry_forward_path = str(boundary_file)

    result: dict[str, Any] = {
        "ok": status_ready,
        "status": "READY" if status_ready else "NOT_READY",
        "decision": READY_DECISION if status_ready else NOT_READY_DECISION,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "source_34i_complete": source_34i_complete,
        "source_34i_status": "SOURCE_34I_READY" if source_34i_complete else "SOURCE_34I_NOT_READY",
        "source_34i_decision": source.get("decision") if source else None,
        "source_34i_report": str(source_path) if source_path else None,
        "source_34i_safety_violation_count": len(source_safety_violations),
        "source_34i_safety_violations": source_safety_violations,
        "phase_34_closed": bool(source.get("phase_34_closed", False)),
        "phase_34_final_seal_digest": source.get("phase_34_final_seal_digest"),
        "phase_34h_tag_commit": source.get("phase_34h_tag_commit"),
        "required_tag_count": source.get("required_tag_count"),
        "present_tag_count": source.get("present_tag_count"),
        "missing_tag_count": source.get("missing_tag_count"),
        "missing_tags": source.get("missing_tags"),
        "no_submit_runtime_readiness_matrix_complete": no_submit_runtime_readiness_matrix_complete,
        "runtime_readiness_status": artifacts.runtime_matrix.get("runtime_readiness_status") if artifacts else None,
        "runtime_readiness_ready_count": artifacts.runtime_matrix.get("runtime_readiness_ready_count") if artifacts else 0,
        "runtime_readiness_blocker_count": artifacts.runtime_matrix.get("runtime_readiness_blocker_count") if artifacts else 0,
        "runtime_readiness_matrix_digest": artifacts.runtime_matrix.get("runtime_readiness_matrix_digest") if artifacts else None,
        "no_submit_runtime_readiness_matrix_path": runtime_matrix_path,
        "paper_transition_blocker_ledger_complete": paper_transition_blocker_ledger_complete,
        "paper_transition_status": artifacts.blocker_ledger.get("paper_transition_status") if artifacts else None,
        "paper_transition_blocker_count": artifacts.blocker_ledger.get("paper_transition_blocker_count") if artifacts else 0,
        "paper_transition_blocker_ledger_digest": artifacts.blocker_ledger.get("paper_transition_blocker_ledger_digest") if artifacts else None,
        "paper_transition_blocker_ledger_path": blocker_ledger_path,
        "safety_boundary_carry_forward_complete": safety_boundary_carry_forward_complete,
        "safety_boundary_status": artifacts.boundary_carry_forward.get("safety_boundary_status") if artifacts else None,
        "safety_boundary_carry_forward_digest": artifacts.boundary_carry_forward.get("safety_boundary_carry_forward_digest") if artifacts else None,
        "safety_boundary_carry_forward_path": boundary_carry_forward_path,
        "accepted_for_runtime_readiness_planning": status_ready,
        "phase_35_planning_only": True,
        "paper_transition_blocked": True,
        "runtime_readiness_unlock_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "next_phase": NEXT_PHASE,
        "errors": errors,
        "report_path": None,
        **false_field_values,
        **git_context(root),
    }

    if write_reports:
        status_suffix = "ready" if status_ready else "not_ready"
        result_file = reports_dir / f"{PATCH_ID}_post_governance_runtime_readiness_planning_{report_ts}_{status_suffix}.json"
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
