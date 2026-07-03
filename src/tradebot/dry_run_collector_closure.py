from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635G"
PATCH_VERSION = "4B.4.3.6.6.35G"
PATCH_NAME = "Dry-Run Collector Closure"
CHECK_NAME = "dry_run_collector_closure"
READY_DECISION = "DRY_RUN_COLLECTOR_CLOSURE_READY_NO_EXECUTION_PROOF_PAPER_BLOCKER_CARRIED_FORWARD"
NOT_READY_DECISION = "DRY_RUN_COLLECTOR_CLOSURE_NOT_READY"
SOURCE_READY_DECISION = "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_NO_SUBMIT_COLLECTOR_GUARD_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.35H"

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
)

NO_EXECUTION_FIELDS = (
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

PAPER_BLOCKERS = (
    {
        "blocker_id": "OPERATOR_COLLECTION_TOKEN_ABSENT",
        "severity": "HARD_BLOCKER",
        "status": "OPEN",
        "note": "Collection token template is not an authorization and no valid token is present.",
    },
    {
        "blocker_id": "PUBLIC_DATA_DRY_RUN_NOT_AUTHORIZED_FOR_EXECUTION",
        "severity": "HARD_BLOCKER",
        "status": "OPEN",
        "note": "Public data dry-run authorization remains false; execution is not granted.",
    },
    {
        "blocker_id": "DRY_RUN_COLLECTOR_NOT_EXECUTABLE_NOW",
        "severity": "HARD_BLOCKER",
        "status": "OPEN",
        "note": "Collector executable-now flag is false and guard is locked.",
    },
    {
        "blocker_id": "NO_SUBMIT_DRY_RUN_COLLECTOR_GUARD_LOCKED",
        "severity": "BOUNDARY_BLOCKER",
        "status": "OPEN",
        "note": "No-submit collector guard remains locked and cannot be relaxed by 35G.",
    },
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


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    branch = git_value(["branch", "--show-current"], repo_root)
    head = git_value(["rev-parse", "--short", "HEAD"], repo_root)
    tags = git_value(["tag", "--list", "4B.4.3.6.6.35*"], repo_root)
    return {
        "git_available": branch is not None or head is not None,
        "git_branch": branch or None,
        "git_head_short": head or None,
        "phase_35_tag_count_observed": len([line for line in (tags or "").splitlines() if line.strip()]),
    }


def latest_source_35f_report(reports_dir: Path) -> Path | None:
    patterns = (
        "4B436635F_public_data_collection_dry_run_*_ready.json",
        "**/4B436635F_public_data_collection_dry_run_*_ready.json",
    )
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(p for p in reports_dir.glob(pattern) if p.is_file())
    unique = sorted(set(matches), key=lambda p: (p.stat().st_mtime, str(p)))
    return unique[-1] if unique else None


def safety_violations(report: dict[str, Any]) -> list[str]:
    return [field for field in FALSE_SAFETY_FIELDS if bool(report.get(field, False))]


def execution_violations(report: dict[str, Any]) -> list[str]:
    return [field for field in NO_EXECUTION_FIELDS if bool(report.get(field, False))]


@dataclass(frozen=True)
class Source35F:
    path: Path | None
    data: dict[str, Any]
    complete: bool
    status: str
    decision: str | None
    safety_violations: tuple[str, ...]
    execution_violations: tuple[str, ...]


def load_source_35f(reports_dir: Path) -> Source35F:
    path = latest_source_35f_report(reports_dir)
    if path is None:
        return Source35F(None, {}, False, "SOURCE_35F_REPORT_MISSING", None, tuple(), tuple())
    try:
        data = read_json(path)
    except Exception as exc:
        return Source35F(path, {}, False, f"SOURCE_35F_REPORT_INVALID:{exc}", None, tuple(), tuple())
    safety = tuple(safety_violations(data))
    execution = tuple(execution_violations(data))
    complete = (
        data.get("status") == "READY"
        and data.get("decision") == SOURCE_READY_DECISION
        and bool(data.get("collection_token_template_complete"))
        and bool(data.get("collection_token_template_is_not_authorization"))
        and bool(data.get("public_market_data_scope_freeze_complete"))
        and bool(data.get("public_market_data_scope_frozen"))
        and bool(data.get("no_submit_dry_run_collector_guard_complete"))
        and bool(data.get("no_submit_dry_run_collector_guard_locked"))
        and not safety
        and not execution
    )
    return Source35F(
        path=path,
        data=data,
        complete=complete,
        status="SOURCE_35F_READY" if complete else "SOURCE_35F_NOT_READY",
        decision=data.get("decision"),
        safety_violations=safety,
        execution_violations=execution,
    )


def build_collector_scope_digest(source: Source35F) -> dict[str, Any]:
    scope_digest_inputs = {
        "source_35f_collection_token_template_digest": source.data.get("collection_token_template_digest"),
        "source_35f_public_market_data_scope_freeze_digest": source.data.get("public_market_data_scope_freeze_digest"),
        "source_35f_no_submit_dry_run_collector_guard_digest": source.data.get("no_submit_dry_run_collector_guard_digest"),
        "source_35f_public_market_data_scope_count": source.data.get("public_market_data_scope_count"),
        "source_35f_public_market_data_scope_frozen": source.data.get("public_market_data_scope_frozen"),
        "source_35f_public_data_collection_scope_ready": source.data.get("public_data_collection_scope_ready"),
    }
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35f_report": str(source.path) if source.path else None,
        "source_35f_decision": source.decision,
        "collector_scope_digest_inputs": scope_digest_inputs,
        "collector_scope_digest_ledger_complete": source.complete,
        "collector_scope_digest_status": (
            "COLLECTOR_SCOPE_DIGEST_READY_SCOPE_FROZEN" if source.complete else "COLLECTOR_SCOPE_DIGEST_BLOCKED_SOURCE_35F_NOT_READY"
        ),
        "collector_scope_relaxed": False,
        "public_market_data_scope_frozen": bool(source.data.get("public_market_data_scope_frozen", False)),
        "public_market_data_scope_count": int(source.data.get("public_market_data_scope_count", 0) or 0),
    }
    payload["collector_scope_digest"] = digest(scope_digest_inputs)
    payload["collector_scope_digest_ledger_digest"] = digest(payload)
    return payload


def build_no_execution_proof_ledger(source: Source35F) -> dict[str, Any]:
    proof_items = [
        {"field": field, "observed_value": bool(source.data.get(field, False)), "expected_value": False}
        for field in NO_EXECUTION_FIELDS
    ]
    no_execution_confirmed = source.complete and not source.execution_violations and all(not item["observed_value"] for item in proof_items)
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35f_report": str(source.path) if source.path else None,
        "source_35f_decision": source.decision,
        "no_execution_proof_items": proof_items,
        "no_execution_proof_item_count": len(proof_items),
        "no_execution_proof_ledger_complete": source.complete,
        "no_execution_confirmed": bool(no_execution_confirmed),
        "no_execution_violation_count": len(source.execution_violations),
        "no_execution_violations": list(source.execution_violations),
        "no_execution_proof_status": (
            "NO_EXECUTION_PROOF_CONFIRMED" if no_execution_confirmed else "NO_EXECUTION_PROOF_BLOCKED_OR_VIOLATED"
        ),
    }
    payload["no_execution_proof_digest"] = digest(payload)
    return payload


def build_paper_blocker_carry_forward(source: Source35F) -> dict[str, Any]:
    blockers = [dict(item) for item in PAPER_BLOCKERS]
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35f_report": str(source.path) if source.path else None,
        "source_35f_decision": source.decision,
        "paper_blockers": blockers,
        "paper_blocker_carry_forward_complete": source.complete,
        "paper_blocker_carry_forward_count": len(blockers),
        "paper_blocker_carry_forward_status": (
            "PAPER_BLOCKER_CARRIED_FORWARD_COLLECTION_DRY_RUN_ONLY" if source.complete else "PAPER_BLOCKER_CARRY_FORWARD_BLOCKED_SOURCE_35F_NOT_READY"
        ),
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
    }
    payload["paper_blocker_carry_forward_digest"] = digest(payload)
    return payload


def evaluate(repo_root: Path | None = None, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    repo_root = repo_root_from(repo_root)
    reports_dir = (reports_dir or (repo_root / "reports" / "recovery")).resolve()
    source = load_source_35f(reports_dir)
    scope_digest = build_collector_scope_digest(source)
    no_execution = build_no_execution_proof_ledger(source)
    paper_blockers = build_paper_blocker_carry_forward(source)

    errors: list[str] = []
    if not source.complete:
        errors.append(source.status)
    if source.safety_violations:
        errors.append("SOURCE_35F_SAFETY_VIOLATIONS:" + ",".join(source.safety_violations))
    if source.execution_violations:
        errors.append("SOURCE_35F_EXECUTION_VIOLATIONS:" + ",".join(source.execution_violations))

    ready = not errors and all(
        [
            scope_digest["collector_scope_digest_ledger_complete"],
            no_execution["no_execution_proof_ledger_complete"],
            no_execution["no_execution_confirmed"],
            paper_blockers["paper_blocker_carry_forward_complete"],
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
        **git_snapshot(repo_root),
        "source_35f_complete": source.complete,
        "source_35f_status": source.status,
        "source_35f_decision": source.decision,
        "source_35f_report": str(source.path) if source.path else None,
        "source_35f_safety_violation_count": len(source.safety_violations),
        "source_35f_safety_violations": list(source.safety_violations),
        "source_35f_execution_violation_count": len(source.execution_violations),
        "source_35f_execution_violations": list(source.execution_violations),
        "source_35f_collection_token_template_digest": source.data.get("collection_token_template_digest"),
        "source_35f_public_market_data_scope_freeze_digest": source.data.get("public_market_data_scope_freeze_digest"),
        "source_35f_no_submit_dry_run_collector_guard_digest": source.data.get("no_submit_dry_run_collector_guard_digest"),
        "phase_34_closed": bool(source.data.get("phase_34_closed", True)),
        "phase_35_planning_only": True,
        "accepted_for_dry_run_collector_closure": ready,
        "collector_scope_digest_ledger_complete": scope_digest["collector_scope_digest_ledger_complete"],
        "collector_scope_digest_status": scope_digest["collector_scope_digest_status"],
        "collector_scope_digest": scope_digest["collector_scope_digest"],
        "collector_scope_digest_ledger_digest": scope_digest["collector_scope_digest_ledger_digest"],
        "collector_scope_relaxed": False,
        "public_market_data_scope_frozen": scope_digest["public_market_data_scope_frozen"],
        "public_market_data_scope_count": scope_digest["public_market_data_scope_count"],
        "no_execution_proof_ledger_complete": no_execution["no_execution_proof_ledger_complete"],
        "no_execution_confirmed": no_execution["no_execution_confirmed"],
        "no_execution_proof_item_count": no_execution["no_execution_proof_item_count"],
        "no_execution_violation_count": no_execution["no_execution_violation_count"],
        "no_execution_violations": no_execution["no_execution_violations"],
        "no_execution_proof_status": no_execution["no_execution_proof_status"],
        "no_execution_proof_digest": no_execution["no_execution_proof_digest"],
        "paper_blocker_carry_forward_complete": paper_blockers["paper_blocker_carry_forward_complete"],
        "paper_blocker_carry_forward_count": paper_blockers["paper_blocker_carry_forward_count"],
        "paper_blocker_carry_forward_status": paper_blockers["paper_blocker_carry_forward_status"],
        "paper_blocker_carry_forward_digest": paper_blockers["paper_blocker_carry_forward_digest"],
        "dry_run_collector_closure_ready": ready,
        "collector_closure_executable_now": False,
        "collector_closure_executed": False,
        "public_data_collection_allowed_now": False,
        "dry_run_collector_executable_now": False,
        "dry_run_collector_executed": False,
        "collector_guard_relaxed": False,
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
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_COLLECTOR_CLOSURE_NO_EXECUTION",
        "runtime_readiness_status": "DRY_RUN_COLLECTOR_CLOSURE_READY_PLANNING_ONLY_NO_SUBMIT" if ready else "DRY_RUN_COLLECTOR_CLOSURE_NOT_READY",
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
        scope_path = reports_dir / f"{PATCH_ID}_collector_scope_digest_{stamp}.json"
        proof_path = reports_dir / f"{PATCH_ID}_no_execution_proof_ledger_{stamp}.json"
        blocker_path = reports_dir / f"{PATCH_ID}_paper_blocker_carry_forward_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_dry_run_collector_closure_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(scope_path, scope_digest)
        write_json(proof_path, no_execution)
        write_json(blocker_path, paper_blockers)
        report.update(
            {
                "collector_scope_digest_path": str(scope_path),
                "no_execution_proof_ledger_path": str(proof_path),
                "paper_blocker_carry_forward_path": str(blocker_path),
                "report_path": str(report_path),
            }
        )
        write_json(report_path, report)
    else:
        report.update(
            {
                "collector_scope_digest_path": None,
                "no_execution_proof_ledger_path": None,
                "paper_blocker_carry_forward_path": None,
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
