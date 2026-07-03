from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634E"
PATCH_VERSION = "4B.4.3.6.6.34E"
PATCH_NAME = "Transition Approval Dry-Run"
READY_DECISION = "TRANSITION_APPROVAL_DRY_RUN_READY_NO_SUBMIT_HANDOFF_LOCKED"
NOT_READY_DECISION = "TRANSITION_APPROVAL_DRY_RUN_NOT_READY"
SOURCE_34D_DECISION = "OPERATOR_DECISION_TOKEN_READY_FINAL_NO_SUBMIT_UNLOCK_BOUNDARY_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34F"


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


def int_value(data: Mapping[str, Any], *paths: str, default: int = 0) -> int:
    raw = value(data, *paths, default=None)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


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


@dataclass(frozen=True)
class Source34DDecisionToken:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34c_complete: bool
    human_review_signature_ledger_complete: bool
    human_review_signature_required: bool
    human_review_signature_present: bool
    human_review_signature_status: str | None
    operator_decision_token_present: bool
    transition_eligibility_dry_run_complete: bool
    transition_eligibility_status: str | None
    final_no_submit_unlock_boundary_complete: bool
    final_no_submit_unlock_boundary_status: str | None
    unlock_boundary_locked: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    submit_boundary_relaxed: bool
    dirty_worktree_blocker_count: int
    dirty_worktree_advisory_only: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None
    human_review_signature_digest: str | None
    transition_eligibility_digest: str | None
    final_no_submit_unlock_boundary_digest: str | None


@dataclass(frozen=True)
class OperatorSignatureTemplate:
    complete: bool
    source_34d_report: str | None
    template_status: str
    signature_required: bool
    signature_present: bool
    operator_decision_token_present: bool
    template_fields: list[str]
    accepted_template_criterion_count: int
    rejected_template_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class EligibilityMatrixFreeze:
    complete: bool
    freeze_status: str
    source_34d_complete: bool
    transition_eligibility_dry_run_complete: bool
    final_no_submit_unlock_boundary_complete: bool
    unlock_boundary_locked: bool
    human_review_signature_present: bool
    operator_decision_token_present: bool
    transition_to_next_phase_allowed: bool
    next_phase_unlock_allowed: bool
    next_phase: str
    matrix_frozen: bool
    freeze_scope: list[str]
    accepted_freeze_criterion_count: int
    rejected_freeze_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class NoSubmitHandoffLedger:
    complete: bool
    handoff_status: str
    next_phase: str
    no_submit_handoff_ready: bool
    handoff_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
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
    submit_boundary_relaxed: bool
    digest: str


@dataclass(frozen=True)
class TransitionApprovalDryRunReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34d_complete: bool
    source_34d_report: str | None
    source_34d_decision: str | None
    operator_signature_template_complete: bool
    operator_signature_template_status: str
    human_review_signature_required: bool
    human_review_signature_present: bool
    operator_decision_token_present: bool
    eligibility_matrix_freeze_complete: bool
    eligibility_matrix_freeze_status: str
    eligibility_matrix_frozen: bool
    no_submit_handoff_ledger_complete: bool
    no_submit_handoff_status: str
    no_submit_handoff_ready: bool
    handoff_performed: bool
    transition_eligibility_dry_run_complete: bool
    transition_eligibility_status: str | None
    final_no_submit_unlock_boundary_complete: bool
    final_no_submit_unlock_boundary_status: str | None
    unlock_boundary_locked: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase: str
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
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
    submit_boundary_relaxed: bool
    manifest_sha256: str | None
    immutable_plan_digest: str | None
    baseline_digest: str | None
    evidence_review_digest: str | None
    no_submit_boundary_digest: str | None
    transition_decision_digest: str | None
    human_review_signature_digest: str | None
    transition_eligibility_digest: str | None
    final_no_submit_unlock_boundary_digest: str | None
    operator_signature_template_digest: str | None
    eligibility_matrix_freeze_digest: str | None
    no_submit_handoff_digest: str | None
    report_path: str | None = None
    operator_signature_template_path: str | None = None
    eligibility_matrix_freeze_path: str | None = None
    no_submit_handoff_ledger_path: str | None = None


def parse_source_34d(repo_root: Path) -> Source34DDecisionToken:
    report_path = find_latest_report(repo_root, "4B436634D_operator_decision_token_*_ready.json")
    if report_path is None:
        return Source34DDecisionToken(False, None, None, None, "missing_34d_ready_report", False, False, True, False, None, False, False, None, False, None, True, False, False, False, False, False, 1, False, None, None, None, None, None, None, None, None, None)

    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34DDecisionToken(False, rel, None, None, error, False, False, True, False, None, False, False, None, False, None, True, False, False, False, False, False, 1, False, None, None, None, None, None, None, None, None, None)

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_34c_complete = bool_value(data, "source_34c_complete", "source_34c_gate.complete")
    signature_ledger_complete = bool_value(data, "human_review_signature_ledger_complete", "human_review_signature_ledger.complete")
    signature_required = bool_value(data, "human_review_signature_required", "human_review_signature_ledger.signature_required", default=True)
    signature_present = bool_value(data, "human_review_signature_present", "human_review_signature_ledger.signature_present")
    signature_status = str_or_none(data, "human_review_signature_status", "human_review_signature_ledger.signature_status")
    token_present = bool_value(data, "operator_decision_token_present", "human_review_signature_ledger.operator_decision_token_present")
    eligibility_complete = bool_value(data, "transition_eligibility_dry_run_complete", "transition_eligibility_dry_run.complete")
    eligibility_status = str_or_none(data, "transition_eligibility_status", "transition_eligibility_dry_run.eligibility_status")
    boundary_complete = bool_value(data, "final_no_submit_unlock_boundary_complete", "final_no_submit_unlock_boundary.complete")
    boundary_status = str_or_none(data, "final_no_submit_unlock_boundary_status", "final_no_submit_unlock_boundary.boundary_status")
    unlock_locked = bool_value(data, "unlock_boundary_locked", "final_no_submit_unlock_boundary.unlock_boundary_locked", default=True)
    transition_allowed = bool_value(data, "transition_to_next_phase_allowed", "final_no_submit_unlock_boundary.transition_to_next_phase_allowed", "transition_eligibility_dry_run.transition_to_next_phase_allowed")
    transition_performed = bool_value(data, "transition_to_next_phase_performed", "final_no_submit_unlock_boundary.transition_to_next_phase_performed", "transition_eligibility_dry_run.transition_to_next_phase_performed")
    next_unlock_allowed = bool_value(data, "next_phase_unlock_allowed", "final_no_submit_unlock_boundary.next_phase_unlock_allowed")
    next_unlock_performed = bool_value(data, "next_phase_unlock_performed", "final_no_submit_unlock_boundary.next_phase_unlock_performed")
    submit_relaxed = bool_value(data, "submit_boundary_relaxed", "final_no_submit_unlock_boundary.submit_boundary_relaxed")
    dirty_blocker_count = int_value(data, "dirty_worktree_blocker_count", "source_34c_gate.dirty_worktree_blocker_count")
    dirty_advisory_only = bool_value(data, "dirty_worktree_advisory_only", "source_34c_gate.dirty_worktree_advisory_only", default=True)

    safety_paths = (
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
    )
    safety_ok = all(false_or_missing(data, path) for path in safety_paths)

    complete = bool(
        status == "READY"
        and decision == SOURCE_34D_DECISION
        and source_34c_complete
        and signature_ledger_complete
        and signature_required
        and not signature_present
        and not token_present
        and eligibility_complete
        and boundary_complete
        and unlock_locked
        and not transition_allowed
        and not transition_performed
        and not next_unlock_allowed
        and not next_unlock_performed
        and not submit_relaxed
        and dirty_blocker_count == 0
        and dirty_advisory_only
        and safety_ok
    )

    return Source34DDecisionToken(
        complete=complete,
        report=rel,
        status=status or None,
        decision=decision or None,
        error=None if complete else "source_34d_gate_not_complete",
        source_34c_complete=source_34c_complete,
        human_review_signature_ledger_complete=signature_ledger_complete,
        human_review_signature_required=signature_required,
        human_review_signature_present=signature_present,
        human_review_signature_status=signature_status,
        operator_decision_token_present=token_present,
        transition_eligibility_dry_run_complete=eligibility_complete,
        transition_eligibility_status=eligibility_status,
        final_no_submit_unlock_boundary_complete=boundary_complete,
        final_no_submit_unlock_boundary_status=boundary_status,
        unlock_boundary_locked=unlock_locked,
        transition_to_next_phase_allowed=transition_allowed,
        transition_to_next_phase_performed=transition_performed,
        next_phase_unlock_allowed=next_unlock_allowed,
        next_phase_unlock_performed=next_unlock_performed,
        submit_boundary_relaxed=submit_relaxed,
        dirty_worktree_blocker_count=dirty_blocker_count,
        dirty_worktree_advisory_only=dirty_advisory_only,
        manifest_sha256=str_or_none(data, "manifest_sha256", "source_34c_gate.manifest_sha256"),
        immutable_plan_digest=str_or_none(data, "immutable_plan_digest", "source_34c_gate.immutable_plan_digest"),
        baseline_digest=str_or_none(data, "baseline_digest", "source_34c_gate.baseline_digest"),
        evidence_review_digest=str_or_none(data, "evidence_review_digest", "source_34c_gate.evidence_review_digest"),
        no_submit_boundary_digest=str_or_none(data, "no_submit_boundary_digest", "source_34c_gate.no_submit_boundary_digest"),
        transition_decision_digest=str_or_none(data, "transition_decision_digest", "source_34c_gate.transition_decision_digest"),
        human_review_signature_digest=str_or_none(data, "human_review_signature_digest", "human_review_signature_ledger.digest"),
        transition_eligibility_digest=str_or_none(data, "transition_eligibility_digest", "transition_eligibility_dry_run.digest"),
        final_no_submit_unlock_boundary_digest=str_or_none(data, "final_no_submit_unlock_boundary_digest", "final_no_submit_unlock_boundary.digest"),
    )


def build_operator_signature_template(source: Source34DDecisionToken) -> OperatorSignatureTemplate:
    fields = [
        "operator_id",
        "operator_statement",
        "source_34d_report",
        "transition_eligibility_digest",
        "final_no_submit_unlock_boundary_digest",
        "utc_signed_at",
    ]
    criteria = [
        {"name": "source_34d_ready", "accepted": source.complete},
        {"name": "signature_template_generated", "accepted": True},
        {"name": "human_signature_required", "accepted": source.human_review_signature_required},
        {"name": "human_signature_absent_no_unlock", "accepted": not source.human_review_signature_present},
        {"name": "operator_decision_token_absent", "accepted": not source.operator_decision_token_present},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    payload = {"source_34d_report": source.report, "template_fields": fields, "criteria": criteria}
    return OperatorSignatureTemplate(
        complete=len(rejected) == 0,
        source_34d_report=source.report,
        template_status="OPERATOR_SIGNATURE_TEMPLATE_READY_NO_SIGNATURE_PRESENT" if not rejected else "OPERATOR_SIGNATURE_TEMPLATE_BLOCKED",
        signature_required=True,
        signature_present=False,
        operator_decision_token_present=False,
        template_fields=fields,
        accepted_template_criterion_count=len(criteria) - len(rejected),
        rejected_template_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_eligibility_matrix_freeze(source: Source34DDecisionToken, template: OperatorSignatureTemplate) -> EligibilityMatrixFreeze:
    freeze_scope = [
        "source_34d_decision",
        "human_review_signature_status",
        "transition_eligibility_status",
        "final_no_submit_unlock_boundary_status",
        "no_submit_safety_flags",
    ]
    criteria = [
        {"name": "source_34d_complete", "accepted": source.complete},
        {"name": "operator_signature_template_complete", "accepted": template.complete},
        {"name": "transition_eligibility_dry_run_complete", "accepted": source.transition_eligibility_dry_run_complete},
        {"name": "final_no_submit_unlock_boundary_complete", "accepted": source.final_no_submit_unlock_boundary_complete},
        {"name": "unlock_boundary_locked", "accepted": source.unlock_boundary_locked},
        {"name": "no_signature_no_unlock", "accepted": not source.human_review_signature_present and not source.operator_decision_token_present},
        {"name": "transition_not_allowed", "accepted": not source.transition_to_next_phase_allowed},
        {"name": "next_phase_unlock_not_allowed", "accepted": not source.next_phase_unlock_allowed},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    payload = {"freeze_scope": freeze_scope, "criteria": criteria, "next_phase": NEXT_PHASE}
    return EligibilityMatrixFreeze(
        complete=len(rejected) == 0,
        freeze_status="ELIGIBILITY_MATRIX_FROZEN_NO_UNLOCK" if not rejected else "ELIGIBILITY_MATRIX_FREEZE_BLOCKED",
        source_34d_complete=source.complete,
        transition_eligibility_dry_run_complete=source.transition_eligibility_dry_run_complete,
        final_no_submit_unlock_boundary_complete=source.final_no_submit_unlock_boundary_complete,
        unlock_boundary_locked=source.unlock_boundary_locked,
        human_review_signature_present=False,
        operator_decision_token_present=False,
        transition_to_next_phase_allowed=False,
        next_phase_unlock_allowed=False,
        next_phase=NEXT_PHASE,
        matrix_frozen=len(rejected) == 0,
        freeze_scope=freeze_scope,
        accepted_freeze_criterion_count=len(criteria) - len(rejected),
        rejected_freeze_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_no_submit_handoff_ledger(source: Source34DDecisionToken, freeze: EligibilityMatrixFreeze) -> NoSubmitHandoffLedger:
    complete = bool(source.complete and freeze.complete)
    payload = {
        "complete": complete,
        "handoff_ready": complete,
        "next_phase": NEXT_PHASE,
        "no_submit_flags": False,
        "handoff_performed": False,
    }
    return NoSubmitHandoffLedger(
        complete=complete,
        handoff_status="NO_SUBMIT_HANDOFF_LEDGER_READY_BOUNDARY_LOCKED" if complete else "NO_SUBMIT_HANDOFF_LEDGER_BLOCKED",
        next_phase=NEXT_PHASE,
        no_submit_handoff_ready=complete,
        handoff_performed=False,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
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
        submit_boundary_relaxed=False,
        digest=stable_json_digest(payload),
    )


def build_report(repo_root: Path, write: bool = False, reports_dir: Path | None = None) -> TransitionApprovalDryRunReport:
    source = parse_source_34d(repo_root)
    template = build_operator_signature_template(source)
    freeze = build_eligibility_matrix_freeze(source, template)
    handoff = build_no_submit_handoff_ledger(source, freeze)

    ok = bool(source.complete and template.complete and freeze.complete and handoff.complete)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report = TransitionApprovalDryRunReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="transition_approval_dry_run",
        status=status,
        ok=ok,
        decision=decision,
        source_34d_complete=source.complete,
        source_34d_report=source.report,
        source_34d_decision=source.decision,
        operator_signature_template_complete=template.complete,
        operator_signature_template_status=template.template_status,
        human_review_signature_required=template.signature_required,
        human_review_signature_present=template.signature_present,
        operator_decision_token_present=template.operator_decision_token_present,
        eligibility_matrix_freeze_complete=freeze.complete,
        eligibility_matrix_freeze_status=freeze.freeze_status,
        eligibility_matrix_frozen=freeze.matrix_frozen,
        no_submit_handoff_ledger_complete=handoff.complete,
        no_submit_handoff_status=handoff.handoff_status,
        no_submit_handoff_ready=handoff.no_submit_handoff_ready,
        handoff_performed=handoff.handoff_performed,
        transition_eligibility_dry_run_complete=source.transition_eligibility_dry_run_complete,
        transition_eligibility_status=source.transition_eligibility_status,
        final_no_submit_unlock_boundary_complete=source.final_no_submit_unlock_boundary_complete,
        final_no_submit_unlock_boundary_status=source.final_no_submit_unlock_boundary_status,
        unlock_boundary_locked=source.unlock_boundary_locked,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        next_phase=NEXT_PHASE,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
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
        submit_boundary_relaxed=False,
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
        baseline_digest=source.baseline_digest,
        evidence_review_digest=source.evidence_review_digest,
        no_submit_boundary_digest=source.no_submit_boundary_digest,
        transition_decision_digest=source.transition_decision_digest,
        human_review_signature_digest=source.human_review_signature_digest,
        transition_eligibility_digest=source.transition_eligibility_digest,
        final_no_submit_unlock_boundary_digest=source.final_no_submit_unlock_boundary_digest,
        operator_signature_template_digest=template.digest,
        eligibility_matrix_freeze_digest=freeze.digest,
        no_submit_handoff_digest=handoff.digest,
    )

    if not write:
        return report

    out_dir = reports_dir or (repo_root / "reports" / "recovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_timestamp()
    suffix = status.lower()
    template_path = out_dir / f"{PATCH_ID}_operator_signature_template_{ts}.json"
    freeze_path = out_dir / f"{PATCH_ID}_eligibility_matrix_freeze_{ts}.json"
    handoff_path = out_dir / f"{PATCH_ID}_no_submit_handoff_ledger_{ts}.json"
    report_path = out_dir / f"{PATCH_ID}_transition_approval_dry_run_{ts}_{suffix}.json"

    template_path.write_text(json.dumps(asdict(template), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    freeze_path.write_text(json.dumps(asdict(freeze), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    handoff_path.write_text(json.dumps(asdict(handoff), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    final_report = TransitionApprovalDryRunReport(
        **{
            **asdict(report),
            "report_path": str(report_path),
            "operator_signature_template_path": str(template_path),
            "eligibility_matrix_freeze_path": str(freeze_path),
            "no_submit_handoff_ledger_path": str(handoff_path),
        }
    )
    report_path.write_text(json.dumps(asdict(final_report), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return final_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path.cwd()
    reports_dir = Path(args.reports_dir) if args.reports_dir else None
    report = build_report(repo_root, write=args.write, reports_dir=reports_dir)
    payload = asdict(report)
    if args.once_json:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
