
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635H"
PATCH_VERSION = "4B.4.3.6.6.35H"
PATCH_NAME = "Runtime Readiness Planning Closure"
CHECK_NAME = "runtime_readiness_planning_closure"
READY_DECISION = "RUNTIME_READINESS_PLANNING_CLOSURE_READY_NO_SUBMIT_PHASE_35_INTERIM_SEALED"
NOT_READY_DECISION = "RUNTIME_READINESS_PLANNING_CLOSURE_NOT_READY"
SOURCE_READY_DECISION = "DRY_RUN_COLLECTOR_CLOSURE_READY_NO_EXECUTION_PROOF_PAPER_BLOCKER_CARRIED_FORWARD"
NEXT_PHASE = "4B.4.3.6.6.35I"

REQUIRED_TAGS = tuple(f"4B.4.3.6.6.35{letter}" for letter in "ABCDEFG")

PHASE_EVIDENCE = (
    {
        "phase": "35A",
        "patch_id": "4B436635A",
        "pattern": "4B436635A_post_governance_runtime_readiness_planning_*_ready.json",
        "decision": "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_READY_NO_SUBMIT_BOUNDARY_CARRIED_FORWARD",
    },
    {
        "phase": "35B",
        "patch_id": "4B436635B",
        "pattern": "4B436635B_runtime_readiness_evidence_expansion_*_ready.json",
        "decision": "RUNTIME_READINESS_EVIDENCE_EXPANSION_READY_NO_SUBMIT_EVIDENCE_PACK_LOCKED",
    },
    {
        "phase": "35C",
        "patch_id": "4B436635C",
        "pattern": "4B436635C_runtime_evidence_collection_plan_*_ready.json",
        "decision": "RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED",
    },
    {
        "phase": "35D",
        "patch_id": "4B436635D",
        "pattern": "4B436635D_collection_preflight_gate_*_ready.json",
        "decision": "COLLECTION_PREFLIGHT_GATE_READY_NO_SUBMIT_EXECUTION_GUARD_LOCKED",
    },
    {
        "phase": "35E",
        "patch_id": "4B436635E",
        "pattern": "4B436635E_dry_run_collection_authorization_*_ready.json",
        "decision": "DRY_RUN_COLLECTION_AUTHORIZATION_READY_NO_SUBMIT_COLLECTION_SEAL_LOCKED",
    },
    {
        "phase": "35F",
        "patch_id": "4B436635F",
        "pattern": "4B436635F_public_data_collection_dry_run_*_ready.json",
        "decision": "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_NO_SUBMIT_COLLECTOR_GUARD_LOCKED",
    },
    {
        "phase": "35G",
        "patch_id": "4B436635G",
        "pattern": "4B436635G_dry_run_collector_closure_*_ready.json",
        "decision": "DRY_RUN_COLLECTOR_CLOSURE_READY_NO_EXECUTION_PROOF_PAPER_BLOCKER_CARRIED_FORWARD",
    },
)

FALSE_SAFETY_FIELDS = (
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
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "approval_performed",
    "simulated_approval_performed",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_environment_enabled",
    "live_environment_enabled",
    "runtime_readiness_unlock_performed",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "public_market_data_collection_performed",
    "runtime_health_probe_performed",
    "runtime_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "collection_preflight_executed",
    "collection_runbook_executed",
    "collection_authorization_unlocked",
    "dry_run_collection_authorization_performed",
    "collection_seal_relaxed",
    "public_data_dry_run_authorized",
    "public_data_collection_allowed_now",
    "dry_run_collector_executed",
    "collector_guard_relaxed",
    "collector_closure_executed",
    "collector_scope_relaxed",
    "phase_35_interim_seal_relaxed",
)

NO_EXECUTION_FIELDS = (
    "collector_closure_executed",
    "dry_run_collector_executed",
    "public_market_data_collection_performed",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "runtime_probe_performed",
    "runtime_health_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "collection_preflight_executed",
    "collection_runbook_executed",
    "collection_authorization_unlocked",
    "collector_guard_relaxed",
    "order_submit_performed",
    "exchange_submit_performed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "src").exists():
            return candidate
    return current


def git_value(args: list[str], repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_tag_set(repo_root: Path) -> set[str]:
    tags = git_value(["tag", "--list", "4B.4.3.6.6.35*"], repo_root)
    return {line.strip() for line in (tags or "").splitlines() if line.strip()}


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    branch = git_value(["branch", "--show-current"], repo_root)
    head = git_value(["rev-parse", "--short", "HEAD"], repo_root)
    tags = git_tag_set(repo_root)
    missing = [tag for tag in REQUIRED_TAGS if tag not in tags]
    present = [tag for tag in REQUIRED_TAGS if tag in tags]
    return {
        "git_available": branch is not None or head is not None,
        "git_branch": branch or None,
        "git_head_short": head or None,
        "phase_35_required_tags": list(REQUIRED_TAGS),
        "phase_35_required_tag_count": len(REQUIRED_TAGS),
        "phase_35_present_tags": present,
        "phase_35_present_tag_count": len(present),
        "phase_35_tag_count_observed": len(tags),
        "phase_35_missing_tags": missing,
        "phase_35_missing_tag_count": len(missing),
        "phase_35_tag_audit_complete": not missing and len(present) == len(REQUIRED_TAGS),
        "phase_35_tag_audit_status": "PHASE_35A_35G_TAG_AUDIT_READY" if not missing and len(present) == len(REQUIRED_TAGS) else "PHASE_35A_35G_TAG_AUDIT_BLOCKED_MISSING_TAGS",
    }


def latest_report(reports_dir: Path, pattern: str) -> Path | None:
    matches: list[Path] = []
    for glob_pattern in (pattern, f"**/{pattern}"):
        matches.extend(p for p in reports_dir.glob(glob_pattern) if p.is_file())
    unique = sorted(set(matches), key=lambda p: (p.stat().st_mtime, str(p)))
    return unique[-1] if unique else None


def latest_source_35g_report(reports_dir: Path) -> Path | None:
    return latest_report(reports_dir, "4B436635G_dry_run_collector_closure_*_ready.json")


def safety_violations(report: dict[str, Any]) -> list[str]:
    return [field for field in FALSE_SAFETY_FIELDS if bool(report.get(field, False))]


def execution_violations(report: dict[str, Any]) -> list[str]:
    return [field for field in NO_EXECUTION_FIELDS if bool(report.get(field, False))]


@dataclass(frozen=True)
class Source35G:
    path: Path | None
    data: dict[str, Any]
    complete: bool
    status: str
    decision: str | None
    safety_violations: tuple[str, ...]
    execution_violations: tuple[str, ...]


def load_source_35g(reports_dir: Path) -> Source35G:
    path = latest_source_35g_report(reports_dir)
    if path is None:
        return Source35G(None, {}, False, "SOURCE_35G_REPORT_MISSING", None, tuple(), tuple())
    try:
        data = read_json(path)
    except Exception as exc:
        return Source35G(path, {}, False, f"SOURCE_35G_REPORT_INVALID:{exc}", None, tuple(), tuple())
    safety = tuple(safety_violations(data))
    execution = tuple(execution_violations(data))
    complete = (
        data.get("status") == "READY"
        and data.get("decision") == SOURCE_READY_DECISION
        and bool(data.get("collector_scope_digest_ledger_complete"))
        and bool(data.get("no_execution_proof_ledger_complete"))
        and bool(data.get("no_execution_confirmed"))
        and int(data.get("no_execution_violation_count", 1) or 0) == 0
        and bool(data.get("paper_blocker_carry_forward_complete"))
        and bool(data.get("paper_transition_blocked", True))
        and not safety
        and not execution
    )
    return Source35G(
        path=path,
        data=data,
        complete=complete,
        status="SOURCE_35G_READY" if complete else "SOURCE_35G_NOT_READY",
        decision=data.get("decision"),
        safety_violations=safety,
        execution_violations=execution,
    )


def build_planning_evidence_acceptance(reports_dir: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for spec in PHASE_EVIDENCE:
        path = latest_report(reports_dir, str(spec["pattern"]))
        if path is None:
            items.append({
                "phase": spec["phase"],
                "patch_id": spec["patch_id"],
                "report_path": None,
                "status": "MISSING",
                "decision": None,
                "accepted": False,
            })
            continue
        try:
            data = read_json(path)
        except Exception as exc:
            items.append({
                "phase": spec["phase"],
                "patch_id": spec["patch_id"],
                "report_path": str(path),
                "status": f"INVALID:{exc}",
                "decision": None,
                "accepted": False,
            })
            continue
        accepted = data.get("status") == "READY" and data.get("decision") == spec["decision"] and not safety_violations(data)
        items.append({
            "phase": spec["phase"],
            "patch_id": spec["patch_id"],
            "report_path": str(path),
            "status": data.get("status"),
            "decision": data.get("decision"),
            "expected_decision": spec["decision"],
            "safety_violation_count": len(safety_violations(data)),
            "accepted": bool(accepted),
        })
    complete = all(item["accepted"] for item in items)
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "planning_evidence_items": items,
        "planning_evidence_item_count": len(items),
        "planning_evidence_accepted_count": sum(1 for item in items if item["accepted"]),
        "planning_evidence_missing_count": sum(1 for item in items if item["report_path"] is None),
        "planning_evidence_acceptance_complete": complete,
        "planning_evidence_accepted": complete,
        "planning_evidence_acceptance_status": "PLANNING_EVIDENCE_ACCEPTED_35A_35G" if complete else "PLANNING_EVIDENCE_ACCEPTANCE_BLOCKED",
    }
    payload["planning_evidence_acceptance_digest"] = digest(payload)
    return payload


def build_phase_35_tag_audit(git_data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "phase_35_tag_audit_complete": bool(git_data["phase_35_tag_audit_complete"]),
        "phase_35_tag_audit_status": git_data["phase_35_tag_audit_status"],
        "phase_35_required_tags": git_data["phase_35_required_tags"],
        "phase_35_required_tag_count": git_data["phase_35_required_tag_count"],
        "phase_35_present_tags": git_data["phase_35_present_tags"],
        "phase_35_present_tag_count": git_data["phase_35_present_tag_count"],
        "phase_35_missing_tags": git_data["phase_35_missing_tags"],
        "phase_35_missing_tag_count": git_data["phase_35_missing_tag_count"],
        "phase_35_tag_count_observed": git_data["phase_35_tag_count_observed"],
    }
    payload["phase_35_tag_audit_digest"] = digest(payload)
    return payload


def build_no_submit_phase_35_interim_seal(source: Source35G, evidence: dict[str, Any], tag_audit: dict[str, Any]) -> dict[str, Any]:
    seal_complete = source.complete and evidence["planning_evidence_acceptance_complete"] and tag_audit["phase_35_tag_audit_complete"]
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35g_report": str(source.path) if source.path else None,
        "source_35g_decision": source.decision,
        "source_35g_complete": source.complete,
        "planning_evidence_acceptance_digest": evidence["planning_evidence_acceptance_digest"],
        "phase_35_tag_audit_digest": tag_audit["phase_35_tag_audit_digest"],
        "no_submit_phase_35_interim_seal_complete": seal_complete,
        "no_submit_phase_35_interim_sealed": seal_complete,
        "no_submit_phase_35_interim_seal_locked": True,
        "phase_35_interim_seal_relaxed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "runtime_overlay_allowed": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "runtime_evidence_collection_performed": False,
        "public_market_data_collection_performed": False,
        "no_submit_phase_35_interim_seal_status": "NO_SUBMIT_PHASE_35_INTERIM_SEAL_LOCKED" if seal_complete else "NO_SUBMIT_PHASE_35_INTERIM_SEAL_BLOCKED",
    }
    payload["no_submit_phase_35_interim_seal_digest"] = digest(payload)
    return payload


def evaluate(repo_root: Path | None = None, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    repo_root = repo_root_from(repo_root)
    reports_dir = (reports_dir or (repo_root / "reports" / "recovery")).resolve()
    source = load_source_35g(reports_dir)
    git_data = git_snapshot(repo_root)
    tag_audit = build_phase_35_tag_audit(git_data)
    evidence = build_planning_evidence_acceptance(reports_dir)
    seal = build_no_submit_phase_35_interim_seal(source, evidence, tag_audit)

    errors: list[str] = []
    if not source.complete:
        errors.append(source.status)
    if source.safety_violations:
        errors.append("SOURCE_35G_SAFETY_VIOLATIONS:" + ",".join(source.safety_violations))
    if source.execution_violations:
        errors.append("SOURCE_35G_EXECUTION_VIOLATIONS:" + ",".join(source.execution_violations))
    if not tag_audit["phase_35_tag_audit_complete"]:
        errors.append("PHASE_35_TAG_AUDIT_INCOMPLETE")
    if not evidence["planning_evidence_acceptance_complete"]:
        errors.append("PLANNING_EVIDENCE_ACCEPTANCE_INCOMPLETE")

    ready = not errors and all(
        [
            source.complete,
            tag_audit["phase_35_tag_audit_complete"],
            evidence["planning_evidence_acceptance_complete"],
            seal["no_submit_phase_35_interim_seal_complete"],
            seal["no_submit_phase_35_interim_seal_locked"],
        ]
    )
    stamp = utc_stamp()

    report: dict[str, Any] = {
        "ok": ready,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "check_name": CHECK_NAME,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "errors": errors,
        **git_data,
        "source_35g_complete": source.complete,
        "source_35g_status": source.status,
        "source_35g_decision": source.decision,
        "source_35g_report": str(source.path) if source.path else None,
        "source_35g_safety_violation_count": len(source.safety_violations),
        "source_35g_safety_violations": list(source.safety_violations),
        "source_35g_execution_violation_count": len(source.execution_violations),
        "source_35g_execution_violations": list(source.execution_violations),
        "source_35g_collector_scope_digest": source.data.get("collector_scope_digest"),
        "source_35g_no_execution_proof_digest": source.data.get("no_execution_proof_digest"),
        "source_35g_paper_blocker_carry_forward_digest": source.data.get("paper_blocker_carry_forward_digest"),
        "source_35g_no_execution_confirmed": bool(source.data.get("no_execution_confirmed", False)),
        "source_35g_no_execution_violation_count": int(source.data.get("no_execution_violation_count", 0) or 0),
        "source_35g_paper_blocker_carry_forward_count": int(source.data.get("paper_blocker_carry_forward_count", 0) or 0),
        "phase_34_closed": bool(source.data.get("phase_34_closed", True)),
        "phase_35_planning_only": True,
        "accepted_for_runtime_readiness_planning_closure": ready,
        "phase_35_planning_closure_ready": ready,
        "planning_evidence_acceptance_complete": evidence["planning_evidence_acceptance_complete"],
        "planning_evidence_accepted": evidence["planning_evidence_accepted"],
        "planning_evidence_item_count": evidence["planning_evidence_item_count"],
        "planning_evidence_accepted_count": evidence["planning_evidence_accepted_count"],
        "planning_evidence_missing_count": evidence["planning_evidence_missing_count"],
        "planning_evidence_acceptance_status": evidence["planning_evidence_acceptance_status"],
        "planning_evidence_acceptance_digest": evidence["planning_evidence_acceptance_digest"],
        "phase_35_tag_audit_digest": tag_audit["phase_35_tag_audit_digest"],
        "no_submit_phase_35_interim_seal_complete": seal["no_submit_phase_35_interim_seal_complete"],
        "no_submit_phase_35_interim_sealed": seal["no_submit_phase_35_interim_sealed"],
        "no_submit_phase_35_interim_seal_locked": seal["no_submit_phase_35_interim_seal_locked"],
        "phase_35_interim_seal_relaxed": False,
        "no_submit_phase_35_interim_seal_status": seal["no_submit_phase_35_interim_seal_status"],
        "no_submit_phase_35_interim_seal_digest": seal["no_submit_phase_35_interim_seal_digest"],
        "paper_blocker_carry_forward_count": int(source.data.get("paper_blocker_carry_forward_count", 4) or 4),
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PHASE_35_INTERIM_SEAL_NO_SUBMIT",
        "runtime_readiness_status": "PHASE_35_INTERIM_SEALED_PLANNING_ONLY_NO_SUBMIT" if ready else "PHASE_35_INTERIM_SEAL_NOT_READY",
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "dry_run_collector_executed": False,
        "collector_closure_executed": False,
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    for field in FALSE_SAFETY_FIELDS:
        report.setdefault(field, False)

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        tag_path = reports_dir / f"{PATCH_ID}_phase_35_tag_audit_{stamp}.json"
        evidence_path = reports_dir / f"{PATCH_ID}_planning_evidence_acceptance_{stamp}.json"
        seal_path = reports_dir / f"{PATCH_ID}_no_submit_phase_35_interim_seal_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_runtime_readiness_planning_closure_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(tag_path, tag_audit)
        write_json(evidence_path, evidence)
        write_json(seal_path, seal)
        report.update(
            {
                "phase_35_tag_audit_path": str(tag_path),
                "planning_evidence_acceptance_path": str(evidence_path),
                "no_submit_phase_35_interim_seal_path": str(seal_path),
                "report_path": str(report_path),
            }
        )
        write_json(report_path, report)
    else:
        report.update(
            {
                "phase_35_tag_audit_path": None,
                "planning_evidence_acceptance_path": None,
                "no_submit_phase_35_interim_seal_path": None,
                "report_path": None,
            }
        )
    return report


def main(argv: list[str] | None = None, *, write_reports: bool = False) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = evaluate(reports_dir=args.reports_dir, write_reports=write_reports)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
