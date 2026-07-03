from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634F"
PATCH_VERSION = "4B.4.3.6.6.34F"
PATCH_NAME = "Operator Signature Validation"
READY_DECISION = "OPERATOR_SIGNATURE_VALIDATION_READY_NO_SUBMIT_APPROVAL_LOCKED"
NOT_READY_DECISION = "OPERATOR_SIGNATURE_VALIDATION_NOT_READY"
SOURCE_34E_DECISION = "TRANSITION_APPROVAL_DRY_RUN_READY_NO_SUBMIT_HANDOFF_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34G"


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
    "handoff_performed",
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


@dataclass(frozen=True)
class Source34ETransitionApproval:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34d_complete: bool
    operator_signature_template_complete: bool
    operator_signature_template_status: str | None
    human_review_signature_required: bool
    human_review_signature_present: bool
    operator_decision_token_present: bool
    eligibility_matrix_freeze_complete: bool
    eligibility_matrix_freeze_status: str | None
    eligibility_matrix_frozen: bool
    no_submit_handoff_ledger_complete: bool
    no_submit_handoff_status: str | None
    no_submit_handoff_ready: bool
    final_no_submit_unlock_boundary_complete: bool
    final_no_submit_unlock_boundary_status: str | None
    transition_eligibility_dry_run_complete: bool
    transition_eligibility_status: str | None
    unlock_boundary_locked: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    submit_boundary_relaxed: bool
    handoff_performed: bool
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


@dataclass(frozen=True)
class SignatureFileSchemaLedger:
    complete: bool
    schema_status: str
    signature_file_required: bool
    signature_file_present: bool
    signature_file_path: str | None
    signature_file_valid: bool
    schema_error: str | None
    required_fields: list[str]
    accepted_schema_criterion_count: int
    rejected_schema_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class EligibilityMatrixDigestMatch:
    complete: bool
    digest_match_status: str
    expected_eligibility_matrix_digest: str | None
    provided_eligibility_matrix_digest: str | None
    eligibility_matrix_digest_match: bool
    expected_no_submit_handoff_digest: str | None
    provided_no_submit_handoff_digest: str | None
    no_submit_handoff_digest_match: bool
    signature_file_present: bool
    signature_file_valid: bool
    accepted_digest_criterion_count: int
    rejected_digest_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class NoSubmitApprovalLedger:
    complete: bool
    approval_status: str
    no_submit_approval_ready: bool
    approval_performed: bool
    signature_file_present: bool
    signature_file_valid: bool
    digest_match_complete: bool
    unlock_boundary_locked: bool
    next_phase: str
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
class OperatorSignatureValidationReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34e_complete: bool
    source_34e_report: str | None
    source_34e_decision: str | None
    signature_file_schema_ledger_complete: bool
    signature_file_schema_status: str
    signature_file_required: bool
    signature_file_present: bool
    signature_file_valid: bool
    eligibility_matrix_digest_match_complete: bool
    eligibility_matrix_digest_match_status: str
    expected_eligibility_matrix_digest: str | None
    provided_eligibility_matrix_digest: str | None
    eligibility_matrix_digest_match: bool
    no_submit_approval_ledger_complete: bool
    no_submit_approval_status: str
    no_submit_approval_ready: bool
    approval_performed: bool
    human_review_signature_required: bool
    human_review_signature_present: bool
    operator_decision_token_present: bool
    eligibility_matrix_frozen: bool
    no_submit_handoff_ready: bool
    unlock_boundary_locked: bool
    next_phase: str
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
    signature_file_schema_digest: str | None
    digest_match_ledger_digest: str | None
    no_submit_approval_digest: str | None
    report_path: str | None = None
    signature_file_schema_ledger_path: str | None = None
    eligibility_matrix_digest_match_path: str | None = None
    no_submit_approval_ledger_path: str | None = None


def parse_source_34e(repo_root: Path) -> Source34ETransitionApproval:
    report_path = find_latest_report(repo_root, "4B436634E_transition_approval_dry_run_*_ready.json")
    if report_path is None:
        return Source34ETransitionApproval(
            complete=False, report=None, status=None, decision=None, error="missing_34e_ready_report",
            source_34d_complete=False, operator_signature_template_complete=False, operator_signature_template_status=None,
            human_review_signature_required=True, human_review_signature_present=False, operator_decision_token_present=False,
            eligibility_matrix_freeze_complete=False, eligibility_matrix_freeze_status=None, eligibility_matrix_frozen=False,
            no_submit_handoff_ledger_complete=False, no_submit_handoff_status=None, no_submit_handoff_ready=False,
            final_no_submit_unlock_boundary_complete=False, final_no_submit_unlock_boundary_status=None,
            transition_eligibility_dry_run_complete=False, transition_eligibility_status=None, unlock_boundary_locked=True,
            next_phase_unlock_allowed=False, next_phase_unlock_performed=False, transition_to_next_phase_allowed=False,
            transition_to_next_phase_performed=False, submit_boundary_relaxed=False, handoff_performed=False,
            manifest_sha256=None, immutable_plan_digest=None, baseline_digest=None, evidence_review_digest=None,
            no_submit_boundary_digest=None, transition_decision_digest=None, human_review_signature_digest=None,
            transition_eligibility_digest=None, final_no_submit_unlock_boundary_digest=None,
            operator_signature_template_digest=None, eligibility_matrix_freeze_digest=None, no_submit_handoff_digest=None,
        )

    data, error = read_json(report_path)
    rel = relative_to_repo(repo_root, report_path)
    if data is None:
        return Source34ETransitionApproval(
            complete=False, report=rel, status=None, decision=None, error=error,
            source_34d_complete=False, operator_signature_template_complete=False, operator_signature_template_status=None,
            human_review_signature_required=True, human_review_signature_present=False, operator_decision_token_present=False,
            eligibility_matrix_freeze_complete=False, eligibility_matrix_freeze_status=None, eligibility_matrix_frozen=False,
            no_submit_handoff_ledger_complete=False, no_submit_handoff_status=None, no_submit_handoff_ready=False,
            final_no_submit_unlock_boundary_complete=False, final_no_submit_unlock_boundary_status=None,
            transition_eligibility_dry_run_complete=False, transition_eligibility_status=None, unlock_boundary_locked=True,
            next_phase_unlock_allowed=False, next_phase_unlock_performed=False, transition_to_next_phase_allowed=False,
            transition_to_next_phase_performed=False, submit_boundary_relaxed=False, handoff_performed=False,
            manifest_sha256=None, immutable_plan_digest=None, baseline_digest=None, evidence_review_digest=None,
            no_submit_boundary_digest=None, transition_decision_digest=None, human_review_signature_digest=None,
            transition_eligibility_digest=None, final_no_submit_unlock_boundary_digest=None,
            operator_signature_template_digest=None, eligibility_matrix_freeze_digest=None, no_submit_handoff_digest=None,
        )

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_34d_complete = bool_value(data, "source_34d_complete", "source_34d_gate.complete")
    template_complete = bool_value(data, "operator_signature_template_complete", "operator_signature_template.complete")
    template_status = str_or_none(data, "operator_signature_template_status", "operator_signature_template.template_status")
    sig_required = bool_value(data, "human_review_signature_required", "operator_signature_template.signature_required", default=True)
    sig_present = bool_value(data, "human_review_signature_present", "operator_signature_template.signature_present")
    token_present = bool_value(data, "operator_decision_token_present", "operator_signature_template.operator_decision_token_present")
    freeze_complete = bool_value(data, "eligibility_matrix_freeze_complete", "eligibility_matrix_freeze.complete")
    freeze_status = str_or_none(data, "eligibility_matrix_freeze_status", "eligibility_matrix_freeze.freeze_status")
    frozen = bool_value(data, "eligibility_matrix_frozen", "eligibility_matrix_freeze.matrix_frozen")
    handoff_complete = bool_value(data, "no_submit_handoff_ledger_complete", "no_submit_handoff_ledger.complete")
    handoff_status = str_or_none(data, "no_submit_handoff_status", "no_submit_handoff_ledger.handoff_status")
    handoff_ready = bool_value(data, "no_submit_handoff_ready", "no_submit_handoff_ledger.no_submit_handoff_ready")
    final_boundary_complete = bool_value(data, "final_no_submit_unlock_boundary_complete")
    final_boundary_status = str_or_none(data, "final_no_submit_unlock_boundary_status")
    eligibility_complete = bool_value(data, "transition_eligibility_dry_run_complete")
    eligibility_status = str_or_none(data, "transition_eligibility_status")
    unlock_locked = bool_value(data, "unlock_boundary_locked", default=True)
    next_unlock_allowed = bool_value(data, "next_phase_unlock_allowed", "no_submit_handoff_ledger.next_phase_unlock_allowed")
    next_unlock_performed = bool_value(data, "next_phase_unlock_performed", "no_submit_handoff_ledger.next_phase_unlock_performed")
    transition_allowed = bool_value(data, "transition_to_next_phase_allowed", "no_submit_handoff_ledger.transition_to_next_phase_allowed")
    transition_performed = bool_value(data, "transition_to_next_phase_performed", "no_submit_handoff_ledger.transition_to_next_phase_performed")
    submit_relaxed = bool_value(data, "submit_boundary_relaxed", "no_submit_handoff_ledger.submit_boundary_relaxed")
    handoff_performed = bool_value(data, "handoff_performed", "no_submit_handoff_ledger.handoff_performed")
    safety_ok = all(false_or_missing(data, path) for path in SAFETY_FALSE_PATHS)

    complete = bool(
        status == "READY"
        and decision == SOURCE_34E_DECISION
        and source_34d_complete
        and template_complete
        and sig_required
        and not sig_present
        and not token_present
        and freeze_complete
        and frozen
        and handoff_complete
        and handoff_ready
        and final_boundary_complete
        and eligibility_complete
        and unlock_locked
        and not next_unlock_allowed
        and not next_unlock_performed
        and not transition_allowed
        and not transition_performed
        and not submit_relaxed
        and not handoff_performed
        and safety_ok
    )

    return Source34ETransitionApproval(
        complete=complete,
        report=rel,
        status=status or None,
        decision=decision or None,
        error=None if complete else "source_34e_gate_not_complete",
        source_34d_complete=source_34d_complete,
        operator_signature_template_complete=template_complete,
        operator_signature_template_status=template_status,
        human_review_signature_required=sig_required,
        human_review_signature_present=sig_present,
        operator_decision_token_present=token_present,
        eligibility_matrix_freeze_complete=freeze_complete,
        eligibility_matrix_freeze_status=freeze_status,
        eligibility_matrix_frozen=frozen,
        no_submit_handoff_ledger_complete=handoff_complete,
        no_submit_handoff_status=handoff_status,
        no_submit_handoff_ready=handoff_ready,
        final_no_submit_unlock_boundary_complete=final_boundary_complete,
        final_no_submit_unlock_boundary_status=final_boundary_status,
        transition_eligibility_dry_run_complete=eligibility_complete,
        transition_eligibility_status=eligibility_status,
        unlock_boundary_locked=unlock_locked,
        next_phase_unlock_allowed=next_unlock_allowed,
        next_phase_unlock_performed=next_unlock_performed,
        transition_to_next_phase_allowed=transition_allowed,
        transition_to_next_phase_performed=transition_performed,
        submit_boundary_relaxed=submit_relaxed,
        handoff_performed=handoff_performed,
        manifest_sha256=str_or_none(data, "manifest_sha256"),
        immutable_plan_digest=str_or_none(data, "immutable_plan_digest"),
        baseline_digest=str_or_none(data, "baseline_digest"),
        evidence_review_digest=str_or_none(data, "evidence_review_digest"),
        no_submit_boundary_digest=str_or_none(data, "no_submit_boundary_digest"),
        transition_decision_digest=str_or_none(data, "transition_decision_digest"),
        human_review_signature_digest=str_or_none(data, "human_review_signature_digest"),
        transition_eligibility_digest=str_or_none(data, "transition_eligibility_digest"),
        final_no_submit_unlock_boundary_digest=str_or_none(data, "final_no_submit_unlock_boundary_digest"),
        operator_signature_template_digest=str_or_none(data, "operator_signature_template_digest"),
        eligibility_matrix_freeze_digest=str_or_none(data, "eligibility_matrix_freeze_digest"),
        no_submit_handoff_digest=str_or_none(data, "no_submit_handoff_digest"),
    )


def load_signature_file(repo_root: Path, signature_file: Path | None) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if signature_file is None:
        return None, None, None
    path = signature_file if signature_file.is_absolute() else repo_root / signature_file
    data, error = read_json(path)
    rel = relative_to_repo(repo_root, path)
    return data, error, rel


def build_signature_file_schema_ledger(source: Source34ETransitionApproval, signature_data: Mapping[str, Any] | None, signature_error: str | None, signature_path: str | None) -> SignatureFileSchemaLedger:
    required_fields = [
        "operator_id",
        "operator_statement",
        "source_34e_report",
        "eligibility_matrix_freeze_digest",
        "no_submit_handoff_digest",
        "no_submit_acknowledgement",
        "utc_signed_at",
        "signature_token_sha256",
    ]
    present = signature_data is not None or signature_error is not None
    missing = [] if signature_data is None else [name for name in required_fields if name not in signature_data]
    valid_shape = bool(signature_data is not None and not missing and not signature_error)
    no_signature_ok = not present
    criteria = [
        {"name": "source_34e_complete", "accepted": source.complete},
        {"name": "signature_file_schema_defined", "accepted": True},
        {"name": "signature_file_absent_no_unlock", "accepted": no_signature_ok},
        {"name": "signature_file_valid_when_present", "accepted": True if no_signature_ok else valid_shape},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    payload = {"required_fields": required_fields, "signature_file_present": present, "signature_file_valid": valid_shape, "criteria": criteria}
    status = "SIGNATURE_FILE_SCHEMA_READY_NO_SIGNATURE_FILE_PRESENT" if no_signature_ok and not rejected else (
        "SIGNATURE_FILE_SCHEMA_READY_VALID_SIGNATURE_FILE_NO_UNLOCK" if valid_shape and not rejected else "SIGNATURE_FILE_SCHEMA_BLOCKED"
    )
    return SignatureFileSchemaLedger(
        complete=len(rejected) == 0,
        schema_status=status,
        signature_file_required=True,
        signature_file_present=present,
        signature_file_path=signature_path,
        signature_file_valid=valid_shape,
        schema_error=signature_error or (f"missing_fields:{','.join(missing)}" if missing else None),
        required_fields=required_fields,
        accepted_schema_criterion_count=len(criteria) - len(rejected),
        rejected_schema_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_digest_match_ledger(source: Source34ETransitionApproval, schema: SignatureFileSchemaLedger, signature_data: Mapping[str, Any] | None) -> EligibilityMatrixDigestMatch:
    provided_eligibility = str(value(signature_data or {}, "eligibility_matrix_freeze_digest", default="")) if signature_data is not None else None
    provided_handoff = str(value(signature_data or {}, "no_submit_handoff_digest", default="")) if signature_data is not None else None
    eligibility_match = bool(schema.signature_file_valid and provided_eligibility == source.eligibility_matrix_freeze_digest)
    handoff_match = bool(schema.signature_file_valid and provided_handoff == source.no_submit_handoff_digest)
    no_signature_ok = not schema.signature_file_present
    criteria = [
        {"name": "source_34e_complete", "accepted": source.complete},
        {"name": "expected_eligibility_digest_present", "accepted": bool(source.eligibility_matrix_freeze_digest)},
        {"name": "expected_handoff_digest_present", "accepted": bool(source.no_submit_handoff_digest)},
        {"name": "signature_absent_digest_match_not_evaluated", "accepted": no_signature_ok},
        {"name": "digest_match_valid_when_signature_present", "accepted": True if no_signature_ok else (eligibility_match and handoff_match)},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    payload = {
        "expected_eligibility_matrix_digest": source.eligibility_matrix_freeze_digest,
        "provided_eligibility_matrix_digest": provided_eligibility,
        "expected_no_submit_handoff_digest": source.no_submit_handoff_digest,
        "provided_no_submit_handoff_digest": provided_handoff,
        "signature_file_present": schema.signature_file_present,
        "criteria": criteria,
    }
    status = "ELIGIBILITY_MATRIX_DIGEST_FROZEN_NO_SIGNATURE_FILE" if no_signature_ok and not rejected else (
        "ELIGIBILITY_MATRIX_DIGEST_MATCH_VALIDATED_NO_UNLOCK" if not rejected else "ELIGIBILITY_MATRIX_DIGEST_MATCH_BLOCKED"
    )
    return EligibilityMatrixDigestMatch(
        complete=len(rejected) == 0,
        digest_match_status=status,
        expected_eligibility_matrix_digest=source.eligibility_matrix_freeze_digest,
        provided_eligibility_matrix_digest=provided_eligibility,
        eligibility_matrix_digest_match=eligibility_match,
        expected_no_submit_handoff_digest=source.no_submit_handoff_digest,
        provided_no_submit_handoff_digest=provided_handoff,
        no_submit_handoff_digest_match=handoff_match,
        signature_file_present=schema.signature_file_present,
        signature_file_valid=schema.signature_file_valid,
        accepted_digest_criterion_count=len(criteria) - len(rejected),
        rejected_digest_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_no_submit_approval_ledger(source: Source34ETransitionApproval, schema: SignatureFileSchemaLedger, digest_match: EligibilityMatrixDigestMatch) -> NoSubmitApprovalLedger:
    complete = bool(source.complete and schema.complete and digest_match.complete)
    signature_validated = bool(schema.signature_file_present and schema.signature_file_valid and digest_match.eligibility_matrix_digest_match and digest_match.no_submit_handoff_digest_match)
    status = "NO_SUBMIT_APPROVAL_LEDGER_READY_SIGNATURE_ABSENT_NO_UNLOCK"
    if signature_validated:
        status = "NO_SUBMIT_APPROVAL_LEDGER_READY_SIGNATURE_VALIDATED_NO_UNLOCK"
    if not complete:
        status = "NO_SUBMIT_APPROVAL_LEDGER_BLOCKED"
    payload = {"complete": complete, "signature_validated": signature_validated, "next_phase": NEXT_PHASE, "unlock": False, "submit": False}
    return NoSubmitApprovalLedger(
        complete=complete,
        approval_status=status,
        no_submit_approval_ready=complete,
        approval_performed=False,
        signature_file_present=schema.signature_file_present,
        signature_file_valid=schema.signature_file_valid,
        digest_match_complete=digest_match.complete,
        unlock_boundary_locked=True,
        next_phase=NEXT_PHASE,
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


def build_report(repo_root: Path, write: bool = False, reports_dir: Path | None = None, signature_file: Path | None = None) -> OperatorSignatureValidationReport:
    source = parse_source_34e(repo_root)
    signature_data, signature_error, signature_path = load_signature_file(repo_root, signature_file)
    schema = build_signature_file_schema_ledger(source, signature_data, signature_error, signature_path)
    digest_match = build_digest_match_ledger(source, schema, signature_data)
    approval = build_no_submit_approval_ledger(source, schema, digest_match)

    ok = bool(source.complete and schema.complete and digest_match.complete and approval.complete)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report = OperatorSignatureValidationReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="operator_signature_validation",
        status=status,
        ok=ok,
        decision=decision,
        source_34e_complete=source.complete,
        source_34e_report=source.report,
        source_34e_decision=source.decision,
        signature_file_schema_ledger_complete=schema.complete,
        signature_file_schema_status=schema.schema_status,
        signature_file_required=schema.signature_file_required,
        signature_file_present=schema.signature_file_present,
        signature_file_valid=schema.signature_file_valid,
        eligibility_matrix_digest_match_complete=digest_match.complete,
        eligibility_matrix_digest_match_status=digest_match.digest_match_status,
        expected_eligibility_matrix_digest=digest_match.expected_eligibility_matrix_digest,
        provided_eligibility_matrix_digest=digest_match.provided_eligibility_matrix_digest,
        eligibility_matrix_digest_match=digest_match.eligibility_matrix_digest_match,
        no_submit_approval_ledger_complete=approval.complete,
        no_submit_approval_status=approval.approval_status,
        no_submit_approval_ready=approval.no_submit_approval_ready,
        approval_performed=approval.approval_performed,
        human_review_signature_required=source.human_review_signature_required,
        human_review_signature_present=source.human_review_signature_present,
        operator_decision_token_present=source.operator_decision_token_present,
        eligibility_matrix_frozen=source.eligibility_matrix_frozen,
        no_submit_handoff_ready=source.no_submit_handoff_ready,
        unlock_boundary_locked=True,
        next_phase=NEXT_PHASE,
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
        manifest_sha256=source.manifest_sha256,
        immutable_plan_digest=source.immutable_plan_digest,
        baseline_digest=source.baseline_digest,
        evidence_review_digest=source.evidence_review_digest,
        no_submit_boundary_digest=source.no_submit_boundary_digest,
        transition_decision_digest=source.transition_decision_digest,
        human_review_signature_digest=source.human_review_signature_digest,
        transition_eligibility_digest=source.transition_eligibility_digest,
        final_no_submit_unlock_boundary_digest=source.final_no_submit_unlock_boundary_digest,
        operator_signature_template_digest=source.operator_signature_template_digest,
        eligibility_matrix_freeze_digest=source.eligibility_matrix_freeze_digest,
        no_submit_handoff_digest=source.no_submit_handoff_digest,
        signature_file_schema_digest=schema.digest,
        digest_match_ledger_digest=digest_match.digest,
        no_submit_approval_digest=approval.digest,
    )

    if not write:
        return report

    out_dir = reports_dir or (repo_root / "reports" / "recovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_timestamp()
    suffix = status.lower()
    schema_path = out_dir / f"{PATCH_ID}_signature_file_schema_ledger_{ts}.json"
    digest_path = out_dir / f"{PATCH_ID}_eligibility_matrix_digest_match_{ts}.json"
    approval_path = out_dir / f"{PATCH_ID}_no_submit_approval_ledger_{ts}.json"
    report_path = out_dir / f"{PATCH_ID}_operator_signature_validation_{ts}_{suffix}.json"

    schema_path.write_text(json.dumps(asdict(schema), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    digest_path.write_text(json.dumps(asdict(digest_match), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    approval_path.write_text(json.dumps(asdict(approval), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    final_report = OperatorSignatureValidationReport(
        **{
            **asdict(report),
            "report_path": str(report_path),
            "signature_file_schema_ledger_path": str(schema_path),
            "eligibility_matrix_digest_match_path": str(digest_path),
            "no_submit_approval_ledger_path": str(approval_path),
        }
    )
    report_path.write_text(json.dumps(asdict(final_report), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return final_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--signature-file", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path.cwd()
    reports_dir = Path(args.reports_dir) if args.reports_dir else None
    signature_file = Path(args.signature_file) if args.signature_file else None
    report = build_report(repo_root, write=args.write, reports_dir=reports_dir, signature_file=signature_file)
    payload = asdict(report)
    if args.once_json:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
