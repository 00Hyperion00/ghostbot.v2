
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634H"
PATCH_VERSION = "4B.4.3.6.6.34H"
PATCH_NAME = "Signature Package Closure"
READY_DECISION = "SIGNATURE_PACKAGE_CLOSURE_READY_NO_SUBMIT_CHAIN_CLOSED"
NOT_READY_DECISION = "SIGNATURE_PACKAGE_CLOSURE_NOT_READY"
SOURCE_34G_DECISION = "SIGNATURE_APPROVAL_PACKAGE_READY_FINAL_NO_SUBMIT_GOVERNANCE_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34I"

REQUIRED_34_TAGS: tuple[str, ...] = tuple(f"4B.4.3.6.6.34{letter}" for letter in "ABCDEFGH")

SAFETY_FALSE_PATHS: tuple[str, ...] = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "live_real_submit_allowed",
    "paper_submit_allowed",
    "exchange_submit_allowed",
    "network_submit_allowed",
    "runtime_overlay_allowed",
    "exchange_submit_performed",
    "order_submit_performed",
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
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "submit_boundary_relaxed",
    "approval_performed",
    "simulated_approval_performed",
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, f"missing:{path}"
    except json.JSONDecodeError as exc:
        return None, f"json_decode:{path}:{exc}"
    except OSError as exc:
        return None, f"os_error:{path}:{exc}"
    if not isinstance(data, dict):
        return None, f"non_object_root:{path}"
    return data, None


def value(data: Mapping[str, Any], *paths: str, default: Any = None) -> Any:
    for path in paths:
        current: Any = data
        found = True
        for part in path.split("."):
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found:
            return current
    return default


def bool_value(data: Mapping[str, Any], *paths: str, default: bool = False) -> bool:
    raw = value(data, *paths, default=None)
    if raw is None:
        return default
    return bool(raw)


def str_or_none(data: Mapping[str, Any], *paths: str) -> str | None:
    raw = value(data, *paths, default=None)
    return str(raw) if raw is not None else None


def false_or_missing(data: Mapping[str, Any], *paths: str) -> bool:
    for path in paths:
        raw = value(data, path, default=None)
        if raw is not None:
            return raw is False
    return True


def stable_json_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_dir = repo_root / "reports" / "recovery"
    matches = sorted(reports_dir.glob(pattern))
    return matches[-1] if matches else None


def run_git(repo_root: Path, *args: str) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout).strip()
    return True, completed.stdout.strip()


@dataclass(frozen=True)
class Source34GSignatureApprovalPackage:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34f_complete: bool
    operator_signature_example_complete: bool
    approval_simulation_dry_run_complete: bool
    final_no_submit_governance_ledger_complete: bool
    governance_locked: bool
    no_submit_approval_ready: bool
    real_operator_signature_present: bool
    signature_file_present: bool
    signature_file_valid: bool
    example_is_not_approval: bool
    simulated_approval_performed: bool
    approval_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    submit_boundary_relaxed: bool
    baseline_digest: str | None
    evidence_review_digest: str | None
    eligibility_matrix_freeze_digest: str | None
    no_submit_approval_digest: str | None
    no_submit_handoff_digest: str | None
    final_no_submit_governance_digest: str | None
    approval_simulation_digest: str | None
    operator_signature_example_digest: str | None
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None
    transition_eligibility_digest: str | None


@dataclass(frozen=True)
class FinalGovernanceAcceptanceLedger:
    complete: bool
    governance_acceptance_status: str
    accepted_for_governance_closure: bool
    source_34g_complete: bool
    source_34g_decision: str | None
    no_submit_approval_ready: bool
    governance_locked: bool
    no_real_signature: bool
    no_approval_performed: bool
    no_simulated_approval_performed: bool
    required_criterion_count: int
    accepted_criterion_count: int
    rejected_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class NoSubmitChainClosureLedger:
    complete: bool
    no_submit_chain_status: str
    no_submit_chain_closed: bool
    governance_locked: bool
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    submit_boundary_relaxed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    order_submit_performed: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    file_move_performed: bool
    report_delete_performed: bool
    destructive_cleanup_performed: bool
    deduplication_action_performed: bool
    approval_performed: bool
    simulated_approval_performed: bool
    digest: str


@dataclass(frozen=True)
class Phase34TagAuditLedger:
    complete: bool
    tag_audit_status: str
    tag_audit_advisory_only: bool
    tag_audit_blocker_count: int
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    required_tag_count: int
    present_tag_count: int
    missing_tag_count: int
    present_tags: list[str]
    missing_tags: list[str]
    tag_audit_note: str
    digest: str


@dataclass(frozen=True)
class SignaturePackageClosureReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34g_complete: bool
    source_34g_report: str | None
    source_34g_decision: str | None
    final_governance_acceptance_complete: bool
    final_governance_acceptance_path: str | None
    governance_acceptance_status: str
    accepted_for_governance_closure: bool
    no_submit_chain_closure_complete: bool
    no_submit_chain_closure_path: str | None
    no_submit_chain_status: str
    no_submit_chain_closed: bool
    phase_34_tag_audit_complete: bool
    phase_34_tag_audit_path: str | None
    tag_audit_status: str
    tag_audit_advisory_only: bool
    tag_audit_blocker_count: int
    required_tag_count: int
    present_tag_count: int
    missing_tag_count: int
    missing_tags: list[str]
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    eligibility_matrix_freeze_digest: str | None
    no_submit_approval_digest: str | None
    no_submit_handoff_digest: str | None
    final_no_submit_governance_digest: str | None
    approval_simulation_digest: str | None
    operator_signature_example_digest: str | None
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    submit_boundary_relaxed: bool
    governance_locked: bool
    real_operator_signature_present: bool
    approval_performed: bool
    simulated_approval_performed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    exchange_submit_allowed: bool
    network_submit_allowed: bool
    runtime_overlay_allowed: bool
    order_submit_performed: bool
    exchange_submit_performed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    archive_execution_allowed: bool
    archive_move_performed: bool
    file_delete_performed: bool
    file_move_performed: bool
    report_delete_performed: bool
    destructive_cleanup_performed: bool
    deduplication_action_performed: bool
    report_path: str | None


def read_source_34g(repo_root: Path) -> Source34GSignatureApprovalPackage:
    report_path = find_latest_report(repo_root, "4B436634G_signature_approval_package_*_ready.json")
    if report_path is None:
        return Source34GSignatureApprovalPackage(False, None, None, None, "source_34g_ready_report_missing", False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, None, None, None, None, None, None, None, None, None, None, None, None, None, None)
    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34GSignatureApprovalPackage(False, rel, None, None, error, False, False, False, False, False, False, False, False, False, False, True, True, True, True, True, True, None, None, None, None, None, None, None, None, None, None, None, None, None, None)

    safety_ok = all(false_or_missing(data, path, f"safety_snapshot.{path}") for path in SAFETY_FALSE_PATHS)
    status = str_or_none(data, "status")
    decision = str_or_none(data, "decision")
    source_34f_complete = bool_value(data, "source_34f_complete", "source_34f_gate.complete")
    operator_signature_example_complete = bool_value(data, "operator_signature_example_complete", "operator_signature_example.complete")
    approval_simulation_dry_run_complete = bool_value(data, "approval_simulation_dry_run_complete", "approval_simulation_dry_run.complete")
    final_no_submit_governance_ledger_complete = bool_value(data, "final_no_submit_governance_ledger_complete", "final_no_submit_governance_ledger.complete")
    governance_locked = bool_value(data, "governance_locked", "final_no_submit_governance_ledger.governance_locked")
    no_submit_approval_ready = bool_value(data, "no_submit_approval_ready", "source_34f_gate.no_submit_approval_ready")
    real_operator_signature_present = bool_value(data, "real_operator_signature_present", "operator_signature_example.real_operator_signature_present")
    signature_file_present = bool_value(data, "signature_file_present", "source_34f_gate.signature_file_present")
    signature_file_valid = bool_value(data, "signature_file_valid", "source_34f_gate.signature_file_valid")
    example_is_not_approval = bool_value(data, "example_is_not_approval", "operator_signature_example.example_is_not_approval")
    simulated_approval_performed = bool_value(data, "simulated_approval_performed", "approval_simulation_dry_run.simulated_approval_performed")
    approval_performed = bool_value(data, "approval_performed", "final_no_submit_governance_ledger.approval_performed")
    next_phase_unlock_allowed = bool_value(data, "next_phase_unlock_allowed", "final_no_submit_governance_ledger.next_phase_unlock_allowed")
    next_phase_unlock_performed = bool_value(data, "next_phase_unlock_performed", "final_no_submit_governance_ledger.next_phase_unlock_performed")
    transition_to_next_phase_allowed = bool_value(data, "transition_to_next_phase_allowed", "final_no_submit_governance_ledger.transition_to_next_phase_allowed")
    transition_to_next_phase_performed = bool_value(data, "transition_to_next_phase_performed", "final_no_submit_governance_ledger.transition_to_next_phase_performed")
    submit_boundary_relaxed = bool_value(data, "submit_boundary_relaxed", "final_no_submit_governance_ledger.submit_boundary_relaxed")

    complete = all((
        status == "READY",
        decision == SOURCE_34G_DECISION,
        source_34f_complete,
        operator_signature_example_complete,
        approval_simulation_dry_run_complete,
        final_no_submit_governance_ledger_complete,
        governance_locked,
        no_submit_approval_ready,
        example_is_not_approval,
        not real_operator_signature_present,
        not signature_file_present,
        not signature_file_valid,
        not simulated_approval_performed,
        not approval_performed,
        not next_phase_unlock_allowed,
        not next_phase_unlock_performed,
        not transition_to_next_phase_allowed,
        not transition_to_next_phase_performed,
        not submit_boundary_relaxed,
        safety_ok,
    ))

    return Source34GSignatureApprovalPackage(
        complete=complete,
        report=rel,
        status=status,
        decision=decision,
        error=None if complete else "source_34g_gate_incomplete_or_unsafe",
        source_34f_complete=source_34f_complete,
        operator_signature_example_complete=operator_signature_example_complete,
        approval_simulation_dry_run_complete=approval_simulation_dry_run_complete,
        final_no_submit_governance_ledger_complete=final_no_submit_governance_ledger_complete,
        governance_locked=governance_locked,
        no_submit_approval_ready=no_submit_approval_ready,
        real_operator_signature_present=real_operator_signature_present,
        signature_file_present=signature_file_present,
        signature_file_valid=signature_file_valid,
        example_is_not_approval=example_is_not_approval,
        simulated_approval_performed=simulated_approval_performed,
        approval_performed=approval_performed,
        next_phase_unlock_allowed=next_phase_unlock_allowed,
        next_phase_unlock_performed=next_phase_unlock_performed,
        transition_to_next_phase_allowed=transition_to_next_phase_allowed,
        transition_to_next_phase_performed=transition_to_next_phase_performed,
        submit_boundary_relaxed=submit_boundary_relaxed,
        baseline_digest=str_or_none(data, "baseline_digest", "source_34f_gate.baseline_digest"),
        evidence_review_digest=str_or_none(data, "evidence_review_digest", "source_34f_gate.evidence_review_digest"),
        eligibility_matrix_freeze_digest=str_or_none(data, "eligibility_matrix_freeze_digest", "source_34f_gate.eligibility_matrix_freeze_digest"),
        no_submit_approval_digest=str_or_none(data, "no_submit_approval_digest", "source_34f_gate.no_submit_approval_digest"),
        no_submit_handoff_digest=str_or_none(data, "no_submit_handoff_digest", "source_34f_gate.no_submit_handoff_digest"),
        final_no_submit_governance_digest=str_or_none(data, "final_no_submit_governance_digest", "final_no_submit_governance_ledger.digest"),
        approval_simulation_digest=str_or_none(data, "approval_simulation_digest", "approval_simulation_dry_run.digest"),
        operator_signature_example_digest=str_or_none(data, "operator_signature_example_digest", "operator_signature_example.digest"),
        manifest_sha256=str_or_none(data, "manifest_sha256", "source_34f_gate.manifest_sha256"),
        immutable_plan_digest=str_or_none(data, "immutable_plan_digest", "source_34f_gate.immutable_plan_digest"),
        no_submit_boundary_digest=str_or_none(data, "no_submit_boundary_digest", "source_34f_gate.no_submit_boundary_digest"),
        transition_decision_digest=str_or_none(data, "transition_decision_digest", "source_34f_gate.transition_decision_digest"),
        transition_eligibility_digest=str_or_none(data, "transition_eligibility_digest", "source_34f_gate.transition_eligibility_digest"),
    )


def build_final_governance_acceptance(source: Source34GSignatureApprovalPackage) -> FinalGovernanceAcceptanceLedger:
    criteria = [
        {"criterion": "source_34g_complete", "accepted": source.complete},
        {"criterion": "operator_signature_example_complete", "accepted": source.operator_signature_example_complete},
        {"criterion": "approval_simulation_dry_run_complete", "accepted": source.approval_simulation_dry_run_complete},
        {"criterion": "final_no_submit_governance_ledger_complete", "accepted": source.final_no_submit_governance_ledger_complete},
        {"criterion": "governance_locked", "accepted": source.governance_locked},
        {"criterion": "no_real_operator_signature", "accepted": not source.real_operator_signature_present},
        {"criterion": "no_approval_performed", "accepted": not source.approval_performed},
        {"criterion": "no_simulated_approval_performed", "accepted": not source.simulated_approval_performed},
    ]
    accepted = sum(1 for item in criteria if item["accepted"])
    rejected = len(criteria) - accepted
    complete = rejected == 0
    payload = {
        "patch_id": PATCH_ID,
        "status": "FINAL_GOVERNANCE_ACCEPTANCE_READY" if complete else "FINAL_GOVERNANCE_ACCEPTANCE_NOT_READY",
        "criteria": criteria,
        "source_34g_report": source.report,
        "source_34g_decision": source.decision,
    }
    return FinalGovernanceAcceptanceLedger(
        complete=complete,
        governance_acceptance_status=str(payload["status"]),
        accepted_for_governance_closure=complete,
        source_34g_complete=source.complete,
        source_34g_decision=source.decision,
        no_submit_approval_ready=source.no_submit_approval_ready,
        governance_locked=source.governance_locked,
        no_real_signature=not source.real_operator_signature_present,
        no_approval_performed=not source.approval_performed,
        no_simulated_approval_performed=not source.simulated_approval_performed,
        required_criterion_count=len(criteria),
        accepted_criterion_count=accepted,
        rejected_criterion_count=rejected,
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_no_submit_chain_closure(source: Source34GSignatureApprovalPackage) -> NoSubmitChainClosureLedger:
    safe = all((
        source.complete,
        source.governance_locked,
        not source.next_phase_unlock_allowed,
        not source.next_phase_unlock_performed,
        not source.transition_to_next_phase_allowed,
        not source.transition_to_next_phase_performed,
        not source.submit_boundary_relaxed,
        not source.approval_performed,
        not source.simulated_approval_performed,
    ))
    payload = {
        "patch_id": PATCH_ID,
        "status": "NO_SUBMIT_CHAIN_CLOSED_LOCKED" if safe else "NO_SUBMIT_CHAIN_NOT_CLOSED",
        "source_34g_report": source.report,
        "next_phase": NEXT_PHASE,
    }
    return NoSubmitChainClosureLedger(
        complete=safe,
        no_submit_chain_status=str(payload["status"]),
        no_submit_chain_closed=safe,
        governance_locked=source.governance_locked,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        submit_boundary_relaxed=False,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=False,
        paper_submit_allowed=False,
        exchange_submit_allowed=False,
        network_submit_allowed=False,
        runtime_overlay_allowed=False,
        order_submit_performed=False,
        exchange_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        file_move_performed=False,
        report_delete_performed=False,
        destructive_cleanup_performed=False,
        deduplication_action_performed=False,
        approval_performed=False,
        simulated_approval_performed=False,
        digest=stable_json_digest(payload),
    )


def build_phase_34_tag_audit(repo_root: Path) -> Phase34TagAuditLedger:
    ok_branch, branch = run_git(repo_root, "branch", "--show-current")
    ok_head, head = run_git(repo_root, "rev-parse", "--short", "HEAD")
    ok_tags, tag_stdout = run_git(repo_root, "tag", "--list", "4B.4.3.6.6.34*")
    git_available = ok_branch or ok_head or ok_tags
    tags = sorted(line.strip() for line in tag_stdout.splitlines() if line.strip()) if ok_tags else []
    present = [tag for tag in REQUIRED_34_TAGS if tag in tags]
    missing = [tag for tag in REQUIRED_34_TAGS if tag not in tags]
    status = "PHASE_34_TAG_AUDIT_READY_ADVISORY_ONLY"
    note = "Tags are audited as advisory in 34H because 34H itself is normally tagged after this patch is committed."
    payload = {
        "patch_id": PATCH_ID,
        "status": status,
        "required_tags": list(REQUIRED_34_TAGS),
        "present_tags": present,
        "missing_tags": missing,
        "git_branch": branch if ok_branch else None,
        "git_head_short": head if ok_head else None,
        "advisory_only": True,
    }
    return Phase34TagAuditLedger(
        complete=True,
        tag_audit_status=status,
        tag_audit_advisory_only=True,
        tag_audit_blocker_count=0,
        git_available=git_available,
        git_branch=branch if ok_branch else None,
        git_head_short=head if ok_head else None,
        required_tag_count=len(REQUIRED_34_TAGS),
        present_tag_count=len(present),
        missing_tag_count=len(missing),
        present_tags=present,
        missing_tags=missing,
        tag_audit_note=note,
        digest=stable_json_digest(payload),
    )


def write_report(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(payload) if hasattr(payload, "__dataclass_fields__") else payload
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return str(path)


def build_report(repo_root: Path, reports_dir: Path | None = None, write_files: bool = False) -> SignaturePackageClosureReport:
    reports = reports_dir or (repo_root / "reports" / "recovery")
    timestamp = utc_timestamp()
    source = read_source_34g(repo_root)
    governance = build_final_governance_acceptance(source)
    no_submit = build_no_submit_chain_closure(source)
    tags = build_phase_34_tag_audit(repo_root)

    ok = all((
        source.complete,
        governance.complete,
        no_submit.complete,
        tags.complete,
        tags.tag_audit_blocker_count == 0,
        not no_submit.next_phase_unlock_allowed,
        not no_submit.next_phase_unlock_performed,
        not no_submit.transition_to_next_phase_allowed,
        not no_submit.transition_to_next_phase_performed,
        not no_submit.submit_boundary_relaxed,
        not no_submit.approval_performed,
        not no_submit.simulated_approval_performed,
    ))
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    governance_path: str | None = None
    no_submit_path: str | None = None
    tag_audit_path: str | None = None
    report_path: str | None = None
    if write_files:
        governance_abs = reports / f"{PATCH_ID}_final_governance_acceptance_{timestamp}.json"
        no_submit_abs = reports / f"{PATCH_ID}_no_submit_chain_closure_{timestamp}.json"
        tag_abs = reports / f"{PATCH_ID}_34_phase_tag_audit_{timestamp}.json"
        report_abs = reports / f"{PATCH_ID}_signature_package_closure_{timestamp}_{status.lower()}.json"
        write_report(governance_abs, governance)
        write_report(no_submit_abs, no_submit)
        write_report(tag_abs, tags)
        governance_path = relative_to_repo(repo_root, governance_abs)
        no_submit_path = relative_to_repo(repo_root, no_submit_abs)
        tag_audit_path = relative_to_repo(repo_root, tag_abs)
        report_path = relative_to_repo(repo_root, report_abs)

    report = SignaturePackageClosureReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="signature_package_closure",
        status=status,
        ok=ok,
        decision=decision,
        source_34g_complete=source.complete,
        source_34g_report=source.report,
        source_34g_decision=source.decision,
        final_governance_acceptance_complete=governance.complete,
        final_governance_acceptance_path=governance_path,
        governance_acceptance_status=governance.governance_acceptance_status,
        accepted_for_governance_closure=governance.accepted_for_governance_closure,
        no_submit_chain_closure_complete=no_submit.complete,
        no_submit_chain_closure_path=no_submit_path,
        no_submit_chain_status=no_submit.no_submit_chain_status,
        no_submit_chain_closed=no_submit.no_submit_chain_closed,
        phase_34_tag_audit_complete=tags.complete,
        phase_34_tag_audit_path=tag_audit_path,
        tag_audit_status=tags.tag_audit_status,
        tag_audit_advisory_only=tags.tag_audit_advisory_only,
        tag_audit_blocker_count=tags.tag_audit_blocker_count,
        required_tag_count=tags.required_tag_count,
        present_tag_count=tags.present_tag_count,
        missing_tag_count=tags.missing_tag_count,
        missing_tags=tags.missing_tags,
        git_available=tags.git_available,
        git_branch=tags.git_branch,
        git_head_short=tags.git_head_short,
        baseline_digest=source.baseline_digest,
        evidence_review_digest=source.evidence_review_digest,
        eligibility_matrix_freeze_digest=source.eligibility_matrix_freeze_digest,
        no_submit_approval_digest=source.no_submit_approval_digest,
        no_submit_handoff_digest=source.no_submit_handoff_digest,
        final_no_submit_governance_digest=source.final_no_submit_governance_digest,
        approval_simulation_digest=source.approval_simulation_digest,
        operator_signature_example_digest=source.operator_signature_example_digest,
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        submit_boundary_relaxed=False,
        governance_locked=source.governance_locked,
        real_operator_signature_present=source.real_operator_signature_present,
        approval_performed=False,
        simulated_approval_performed=False,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=False,
        paper_submit_allowed=False,
        exchange_submit_allowed=False,
        network_submit_allowed=False,
        runtime_overlay_allowed=False,
        order_submit_performed=False,
        exchange_submit_performed=False,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        archive_execution_allowed=False,
        archive_move_performed=False,
        file_delete_performed=False,
        file_move_performed=False,
        report_delete_performed=False,
        destructive_cleanup_performed=False,
        deduplication_action_performed=False,
        report_path=report_path,
    )
    if write_files and report_path is not None:
        write_report(repo_root / report_path, report)
    return report


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    report = build_report(repo_root, reports_dir=reports_dir, write_files=args.write)
    if args.once_json:
        print(json.dumps(asdict(report), sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
