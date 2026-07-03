from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PATCH_ID = "4B436635B"
PATCH_VERSION = "4B.4.3.6.6.35B"
PATCH_NAME = "Runtime Readiness Evidence Expansion"
CHECK_NAME = "runtime_readiness_evidence_expansion"
READY_DECISION = "RUNTIME_READINESS_EVIDENCE_EXPANSION_READY_NO_SUBMIT_EVIDENCE_PACK_LOCKED"
NOT_READY_DECISION = "RUNTIME_READINESS_EVIDENCE_EXPANSION_NOT_READY"
SOURCE_DECISION = "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_READY_NO_SUBMIT_BOUNDARY_CARRIED_FORWARD"
NEXT_PHASE = "4B.4.3.6.6.35C"

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
    "paper_transition_criteria_met",
    "paper_transition_ready",
)

READINESS_BLOCKER_DETAILS: tuple[dict[str, Any], ...] = (
    {
        "code": "RUNTIME_SERVICE_BOOTSTRAP_EVIDENCE_REQUIRED",
        "severity": "BLOCKER",
        "domain": "runtime_bootstrap",
        "description": "Runtime health/status bootstrap evidence is required under no-submit mode.",
        "required_evidence": "health/status snapshot pack with exchange/network/order submit disabled",
        "current_state": "not_collected",
        "resolution_gate": "future_no_submit_runtime_evidence_collection",
        "owner": "runtime_operations",
    },
    {
        "code": "OPERATOR_COCKPIT_STATUS_CONTRACT_EVIDENCE_REQUIRED",
        "severity": "BLOCKER",
        "domain": "operator_cockpit_contract",
        "description": "Operator cockpit status contract replay evidence is required before any paper candidate.",
        "required_evidence": "stable API/status replay showing deterministic fields and no submit permissions",
        "current_state": "not_collected",
        "resolution_gate": "future_status_contract_replay_gate",
        "owner": "operator_governance",
    },
    {
        "code": "PUBLIC_MARKET_DATA_RUNTIME_EVIDENCE_REQUIRED",
        "severity": "BLOCKER",
        "domain": "market_data_public_only",
        "description": "Public market-data runtime observation is required without private account/order access.",
        "required_evidence": "public market-data ingestion runbook and evidence pack",
        "current_state": "not_collected",
        "resolution_gate": "future_public_data_observation_gate",
        "owner": "data_operations",
    },
    {
        "code": "RISK_BOUNDARY_RUNTIME_ASSERTIONS_REQUIRED",
        "severity": "BLOCKER",
        "domain": "risk_boundary_assertions",
        "description": "Runtime assertions must prove every submit path remains fail-closed.",
        "required_evidence": "assertion report covering exchange_submit/network_submit/paper/live/runtime_overlay flags",
        "current_state": "not_collected",
        "resolution_gate": "future_runtime_safety_assertion_gate",
        "owner": "risk_management",
    },
    {
        "code": "PAPER_TRANSITION_OPERATOR_GATE_REQUIRED",
        "severity": "BLOCKER",
        "domain": "paper_transition_governance",
        "description": "A separate operator approval gate is required before paper transition can be considered.",
        "required_evidence": "operator approval ledger and explicit future phase decision",
        "current_state": "absent",
        "resolution_gate": "future_operator_paper_transition_gate",
        "owner": "operator_governance",
    },
)

PAPER_TRANSITION_CRITERIA: tuple[dict[str, Any], ...] = (
    {
        "criterion": "phase_34_final_seal_verified",
        "required": True,
        "met": True,
        "evidence_source": "source_35a.phase_34_closed + source_35a.source_34i_complete",
    },
    {
        "criterion": "no_submit_boundary_carried_forward",
        "required": True,
        "met": True,
        "evidence_source": "source_35a.safety_boundary_carry_forward_complete",
    },
    {
        "criterion": "runtime_bootstrap_evidence_collected",
        "required": True,
        "met": False,
        "blocking_code": "RUNTIME_SERVICE_BOOTSTRAP_EVIDENCE_REQUIRED",
    },
    {
        "criterion": "operator_cockpit_contract_replayed",
        "required": True,
        "met": False,
        "blocking_code": "OPERATOR_COCKPIT_STATUS_CONTRACT_EVIDENCE_REQUIRED",
    },
    {
        "criterion": "public_market_data_runtime_observed",
        "required": True,
        "met": False,
        "blocking_code": "PUBLIC_MARKET_DATA_RUNTIME_EVIDENCE_REQUIRED",
    },
    {
        "criterion": "operator_paper_transition_approval_present",
        "required": True,
        "met": False,
        "blocking_code": "PAPER_TRANSITION_OPERATOR_GATE_REQUIRED",
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
        reports_dir.glob("4B436635A_post_governance_runtime_readiness_planning_*_ready.json"),
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
class EvidenceArtifacts:
    blocker_detail_ledger: dict[str, Any]
    criteria_matrix: dict[str, Any]
    runtime_evidence_pack: dict[str, Any]


def build_blocker_detail_ledger(source: Mapping[str, Any]) -> dict[str, Any]:
    blockers = [dict(row) for row in READINESS_BLOCKER_DETAILS]
    by_severity: dict[str, int] = {}
    for row in blockers:
        severity = str(row.get("severity", "UNKNOWN"))
        by_severity[severity] = by_severity.get(severity, 0) + 1
    ledger: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ledger_name": "readiness_blocker_detail_ledger",
        "source_35a_report": source.get("source_report_path"),
        "source_35a_runtime_readiness_blocker_count": source.get("runtime_readiness_blocker_count"),
        "source_35a_paper_transition_blocker_count": source.get("paper_transition_blocker_count"),
        "readiness_blocker_details": blockers,
        "readiness_blocker_detail_count": len(blockers),
        "readiness_blocker_severity_counts": by_severity,
        "readiness_blocker_detail_status": "READINESS_BLOCKER_DETAILS_EXPANDED_PLANNING_ONLY",
        "readiness_blocker_detail_ledger_complete": True,
        "runtime_readiness_ready_count": 0,
        "runtime_readiness_evidence_expanded": True,
        "paper_transition_blocked": True,
        "paper_transition_unblocked": False,
        "approved_for_paper_transition": False,
    }
    ledger["readiness_blocker_detail_ledger_digest"] = sha256_json(ledger)
    return ledger


def build_criteria_matrix(source: Mapping[str, Any]) -> dict[str, Any]:
    rows = [dict(row) for row in PAPER_TRANSITION_CRITERIA]
    met_count = sum(1 for row in rows if row.get("met") is True)
    open_count = sum(1 for row in rows if row.get("required") is True and row.get("met") is not True)
    matrix: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "matrix_name": "paper_transition_criteria_matrix",
        "source_35a_report": source.get("source_report_path"),
        "source_35a_phase_34_final_seal_digest": source.get("phase_34_final_seal_digest"),
        "source_35a_runtime_readiness_matrix_digest": source.get("runtime_readiness_matrix_digest"),
        "paper_transition_criteria": rows,
        "paper_transition_criteria_count": len(rows),
        "paper_transition_criteria_met_count": met_count,
        "paper_transition_criteria_open_count": open_count,
        "paper_transition_criteria_met": False,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_CRITERIA_NOT_MET_BLOCKED",
        "paper_transition_criteria_matrix_complete": True,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
    }
    matrix["paper_transition_criteria_matrix_digest"] = sha256_json(matrix)
    return matrix


def build_runtime_evidence_pack(source: Mapping[str, Any], blocker_ledger: Mapping[str, Any], criteria_matrix: Mapping[str, Any]) -> dict[str, Any]:
    pack_items = [
        {
            "item": "source_35a_runtime_readiness_matrix",
            "status": "REFERENCED",
            "digest": source.get("runtime_readiness_matrix_digest"),
        },
        {
            "item": "readiness_blocker_detail_ledger",
            "status": "CREATED",
            "digest": blocker_ledger.get("readiness_blocker_detail_ledger_digest"),
        },
        {
            "item": "paper_transition_criteria_matrix",
            "status": "CREATED",
            "digest": criteria_matrix.get("paper_transition_criteria_matrix_digest"),
        },
        {
            "item": "safety_boundary_carry_forward",
            "status": "REFERENCED",
            "digest": source.get("safety_boundary_carry_forward_digest"),
        },
    ]
    pack: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "pack_name": "no_submit_runtime_evidence_pack",
        "source_35a_report": source.get("source_report_path"),
        "runtime_evidence_pack_items": pack_items,
        "runtime_evidence_pack_item_count": len(pack_items),
        "no_submit_runtime_evidence_pack_complete": True,
        "runtime_evidence_pack_status": "NO_SUBMIT_RUNTIME_EVIDENCE_PACK_READY_FOR_FUTURE_COLLECTION",
        "runtime_evidence_pack_is_no_submit_only": True,
        "runtime_evidence_collection_performed": False,
        "runtime_readiness_unlock_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_unblocked": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
    }
    pack["no_submit_runtime_evidence_pack_digest"] = sha256_json(pack)
    return pack


def build_artifacts(source: Mapping[str, Any]) -> EvidenceArtifacts:
    blocker_ledger = build_blocker_detail_ledger(source)
    criteria_matrix = build_criteria_matrix(source)
    runtime_pack = build_runtime_evidence_pack(source, blocker_ledger, criteria_matrix)
    return EvidenceArtifacts(
        blocker_detail_ledger=blocker_ledger,
        criteria_matrix=criteria_matrix,
        runtime_evidence_pack=runtime_pack,
    )


def source_35a_is_complete(source: Mapping[str, Any], source_safety_violations: list[str]) -> bool:
    return bool(
        source
        and source.get("status") == "READY"
        and source.get("decision") == SOURCE_DECISION
        and source.get("source_34i_complete") is True
        and source.get("phase_34_closed") is True
        and source.get("no_submit_runtime_readiness_matrix_complete") is True
        and source.get("paper_transition_blocker_ledger_complete") is True
        and source.get("safety_boundary_carry_forward_complete") is True
        and source.get("accepted_for_runtime_readiness_planning") is True
        and source.get("phase_35_planning_only") is True
        and source.get("paper_transition_blocked") is True
        and bool_false(source.get("paper_transition_unblocked", False))
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
        errors.append("SOURCE_35A_READY_REPORT_MISSING")
    else:
        try:
            source = read_json(source_path)
            source["source_report_path"] = str(source_path)
        except Exception as exc:
            errors.append(f"SOURCE_35A_REPORT_READ_FAILED:{exc}")

    source_safety_violations = safety_violations(source) if source else []
    source_35a_complete = source_35a_is_complete(source, source_safety_violations)
    if source and not source_35a_complete:
        errors.append("SOURCE_35A_NOT_READY_OR_SAFETY_VIOLATION")

    artifacts = build_artifacts(source) if source else None
    readiness_blocker_detail_ledger_complete = bool(artifacts and artifacts.blocker_detail_ledger.get("readiness_blocker_detail_ledger_complete"))
    paper_transition_criteria_matrix_complete = bool(artifacts and artifacts.criteria_matrix.get("paper_transition_criteria_matrix_complete"))
    no_submit_runtime_evidence_pack_complete = bool(artifacts and artifacts.runtime_evidence_pack.get("no_submit_runtime_evidence_pack_complete"))

    status_ready = bool(
        source_35a_complete
        and readiness_blocker_detail_ledger_complete
        and paper_transition_criteria_matrix_complete
        and no_submit_runtime_evidence_pack_complete
        and not errors
    )

    blocker_detail_ledger_path: str | None = None
    criteria_matrix_path: str | None = None
    runtime_evidence_pack_path: str | None = None

    if write_reports and artifacts is not None:
        blocker_file = reports_dir / f"{PATCH_ID}_readiness_blocker_detail_ledger_{report_ts}.json"
        criteria_file = reports_dir / f"{PATCH_ID}_paper_transition_criteria_matrix_{report_ts}.json"
        pack_file = reports_dir / f"{PATCH_ID}_no_submit_runtime_evidence_pack_{report_ts}.json"
        write_json(blocker_file, artifacts.blocker_detail_ledger)
        write_json(criteria_file, artifacts.criteria_matrix)
        write_json(pack_file, artifacts.runtime_evidence_pack)
        blocker_detail_ledger_path = str(blocker_file)
        criteria_matrix_path = str(criteria_file)
        runtime_evidence_pack_path = str(pack_file)

    false_field_values = {field: False for field in FALSE_SAFETY_FIELDS}
    result: dict[str, Any] = {
        "ok": status_ready,
        "status": "READY" if status_ready else "NOT_READY",
        "decision": READY_DECISION if status_ready else NOT_READY_DECISION,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "source_35a_complete": source_35a_complete,
        "source_35a_status": "SOURCE_35A_READY" if source_35a_complete else "SOURCE_35A_NOT_READY",
        "source_35a_decision": source.get("decision") if source else None,
        "source_35a_report": str(source_path) if source_path else None,
        "source_35a_safety_violation_count": len(source_safety_violations),
        "source_35a_safety_violations": source_safety_violations,
        "source_35a_runtime_readiness_blocker_count": source.get("runtime_readiness_blocker_count"),
        "source_35a_paper_transition_blocker_count": source.get("paper_transition_blocker_count"),
        "phase_34_closed": bool(source.get("phase_34_closed", False)),
        "phase_35_planning_only": True,
        "readiness_blocker_detail_ledger_complete": readiness_blocker_detail_ledger_complete,
        "readiness_blocker_detail_status": artifacts.blocker_detail_ledger.get("readiness_blocker_detail_status") if artifacts else None,
        "readiness_blocker_detail_count": artifacts.blocker_detail_ledger.get("readiness_blocker_detail_count") if artifacts else 0,
        "readiness_blocker_detail_ledger_digest": artifacts.blocker_detail_ledger.get("readiness_blocker_detail_ledger_digest") if artifacts else None,
        "readiness_blocker_detail_ledger_path": blocker_detail_ledger_path,
        "paper_transition_criteria_matrix_complete": paper_transition_criteria_matrix_complete,
        "paper_transition_criteria_count": artifacts.criteria_matrix.get("paper_transition_criteria_count") if artifacts else 0,
        "paper_transition_criteria_met_count": artifacts.criteria_matrix.get("paper_transition_criteria_met_count") if artifacts else 0,
        "paper_transition_criteria_open_count": artifacts.criteria_matrix.get("paper_transition_criteria_open_count") if artifacts else 0,
        "paper_transition_criteria_matrix_digest": artifacts.criteria_matrix.get("paper_transition_criteria_matrix_digest") if artifacts else None,
        "paper_transition_criteria_matrix_path": criteria_matrix_path,
        "no_submit_runtime_evidence_pack_complete": no_submit_runtime_evidence_pack_complete,
        "runtime_evidence_pack_status": artifacts.runtime_evidence_pack.get("runtime_evidence_pack_status") if artifacts else None,
        "runtime_evidence_pack_item_count": artifacts.runtime_evidence_pack.get("runtime_evidence_pack_item_count") if artifacts else 0,
        "no_submit_runtime_evidence_pack_digest": artifacts.runtime_evidence_pack.get("no_submit_runtime_evidence_pack_digest") if artifacts else None,
        "no_submit_runtime_evidence_pack_path": runtime_evidence_pack_path,
        "runtime_readiness_evidence_expanded": status_ready,
        "runtime_readiness_status": "RUNTIME_READINESS_EVIDENCE_EXPANDED_PLANNING_ONLY_PAPER_BLOCKED" if status_ready else "RUNTIME_READINESS_EVIDENCE_EXPANSION_NOT_READY",
        "paper_transition_blocked": True,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_CRITERIA_OPEN_NO_SUBMIT",
        "paper_transition_ready": False,
        "runtime_readiness_ready_count": 0,
        "runtime_readiness_blocker_count": artifacts.blocker_detail_ledger.get("readiness_blocker_detail_count") if artifacts else 0,
        "accepted_for_runtime_readiness_evidence_expansion": status_ready,
        "next_phase": NEXT_PHASE,
        "errors": errors,
        "report_path": None,
        **false_field_values,
        **git_context(root),
    }

    if write_reports:
        status_suffix = "ready" if status_ready else "not_ready"
        result_file = reports_dir / f"{PATCH_ID}_runtime_readiness_evidence_expansion_{report_ts}_{status_suffix}.json"
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
