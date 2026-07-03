
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436634G"
PATCH_VERSION = "4B.4.3.6.6.34G"
PATCH_NAME = "Signature Approval Package"
READY_DECISION = "SIGNATURE_APPROVAL_PACKAGE_READY_FINAL_NO_SUBMIT_GOVERNANCE_LOCKED"
NOT_READY_DECISION = "SIGNATURE_APPROVAL_PACKAGE_NOT_READY"
SOURCE_34F_DECISION = "OPERATOR_SIGNATURE_VALIDATION_READY_NO_SUBMIT_APPROVAL_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.34H"

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
    "approval_performed",
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
class Source34FOperatorSignatureValidation:
    complete: bool
    report: str | None
    status: str | None
    decision: str | None
    error: str | None
    source_34e_complete: bool
    signature_file_schema_ledger_complete: bool
    signature_file_required: bool
    signature_file_present: bool
    signature_file_valid: bool
    eligibility_matrix_digest_match_complete: bool
    eligibility_matrix_digest_match: bool
    no_submit_approval_ledger_complete: bool
    no_submit_approval_ready: bool
    unlock_boundary_locked: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    submit_boundary_relaxed: bool
    approval_performed: bool
    expected_eligibility_matrix_digest: str | None
    provided_eligibility_matrix_digest: str | None
    eligibility_matrix_freeze_digest: str | None
    no_submit_handoff_digest: str | None
    no_submit_approval_digest: str | None
    signature_file_schema_digest: str | None
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


@dataclass(frozen=True)
class OperatorSignatureExampleLedger:
    complete: bool
    example_status: str
    real_operator_signature_present: bool
    example_is_not_approval: bool
    signature_file_schema_version: str
    required_signature_fields: list[str]
    example_signature_payload: dict[str, Any]
    digest: str


@dataclass(frozen=True)
class ApprovalSimulationDryRunLedger:
    complete: bool
    simulation_status: str
    simulation_dry_run_only: bool
    real_operator_signature_present: bool
    simulated_signature_schema_valid: bool
    simulated_digest_match: bool
    simulated_approval_performed: bool
    transition_to_next_phase_allowed: bool
    transition_to_next_phase_performed: bool
    next_phase_unlock_allowed: bool
    next_phase_unlock_performed: bool
    accepted_simulation_criterion_count: int
    rejected_simulation_criterion_count: int
    criteria: list[dict[str, Any]]
    digest: str


@dataclass(frozen=True)
class FinalNoSubmitGovernanceLedger:
    complete: bool
    governance_status: str
    governance_locked: bool
    approval_performed: bool
    simulated_approval_performed: bool
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
class SignatureApprovalPackageReport:
    patch_id: str
    patch_version: str
    check_name: str
    status: str
    ok: bool
    decision: str
    source_34f_complete: bool
    source_34f_report: str | None
    source_34f_decision: str | None
    operator_signature_example_complete: bool
    operator_signature_example_status: str
    real_operator_signature_present: bool
    example_is_not_approval: bool
    approval_simulation_dry_run_complete: bool
    approval_simulation_status: str
    simulated_signature_schema_valid: bool
    simulated_digest_match: bool
    simulated_approval_performed: bool
    final_no_submit_governance_ledger_complete: bool
    final_no_submit_governance_status: str
    governance_locked: bool
    approval_performed: bool
    signature_file_required: bool
    signature_file_present: bool
    signature_file_valid: bool
    eligibility_matrix_digest_match: bool
    no_submit_approval_ready: bool
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
    expected_eligibility_matrix_digest: str | None
    provided_eligibility_matrix_digest: str | None
    eligibility_matrix_freeze_digest: str | None
    no_submit_handoff_digest: str | None
    no_submit_approval_digest: str | None
    signature_file_schema_digest: str | None
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
    operator_signature_example_digest: str | None
    approval_simulation_digest: str | None
    final_no_submit_governance_digest: str | None
    report_path: str | None = None
    operator_signature_example_path: str | None = None
    approval_simulation_dry_run_path: str | None = None
    final_no_submit_governance_ledger_path: str | None = None


def _empty_source(error: str, report: str | None = None) -> Source34FOperatorSignatureValidation:
    return Source34FOperatorSignatureValidation(
        complete=False, report=report, status=None, decision=None, error=error,
        source_34e_complete=False, signature_file_schema_ledger_complete=False,
        signature_file_required=True, signature_file_present=False, signature_file_valid=False,
        eligibility_matrix_digest_match_complete=False, eligibility_matrix_digest_match=False,
        no_submit_approval_ledger_complete=False, no_submit_approval_ready=False,
        unlock_boundary_locked=True, next_phase_unlock_allowed=False, next_phase_unlock_performed=False,
        transition_to_next_phase_allowed=False, transition_to_next_phase_performed=False,
        submit_boundary_relaxed=False, approval_performed=False,
        expected_eligibility_matrix_digest=None, provided_eligibility_matrix_digest=None,
        eligibility_matrix_freeze_digest=None, no_submit_handoff_digest=None,
        no_submit_approval_digest=None, signature_file_schema_digest=None,
        manifest_sha256=None, immutable_plan_digest=None, baseline_digest=None,
        evidence_review_digest=None, no_submit_boundary_digest=None,
        transition_decision_digest=None, human_review_signature_digest=None,
        transition_eligibility_digest=None, final_no_submit_unlock_boundary_digest=None,
        operator_signature_template_digest=None,
    )


def parse_source_34f(repo_root: Path) -> Source34FOperatorSignatureValidation:
    report_path = find_latest_report(repo_root, "4B436634F_operator_signature_validation_*_ready.json")
    if report_path is None:
        return _empty_source("missing_34f_ready_report")
    rel = relative_to_repo(repo_root, report_path)
    data, error = read_json(report_path)
    if data is None:
        return _empty_source(error or "invalid_34f_ready_report", rel)

    status = str(value(data, "status", default=""))
    decision = str(value(data, "decision", default=""))
    source_34e_complete = bool_value(data, "source_34e_complete", "source_34e_gate.complete")
    schema_complete = bool_value(data, "signature_file_schema_ledger_complete", "signature_file_schema_ledger.complete")
    sig_required = bool_value(data, "signature_file_required", "signature_file_schema_ledger.signature_file_required", default=True)
    sig_present = bool_value(data, "signature_file_present", "signature_file_schema_ledger.signature_file_present")
    sig_valid = bool_value(data, "signature_file_valid", "signature_file_schema_ledger.signature_file_valid")
    digest_complete = bool_value(data, "eligibility_matrix_digest_match_complete", "eligibility_matrix_digest_match.complete")
    digest_match = bool_value(data, "eligibility_matrix_digest_match", "eligibility_matrix_digest_match.eligibility_matrix_digest_match")
    approval_complete = bool_value(data, "no_submit_approval_ledger_complete", "no_submit_approval_ledger.complete")
    approval_ready = bool_value(data, "no_submit_approval_ready", "no_submit_approval_ledger.no_submit_approval_ready")
    unlock_locked = bool_value(data, "unlock_boundary_locked", default=True)
    next_allowed = bool_value(data, "next_phase_unlock_allowed", "no_submit_approval_ledger.next_phase_unlock_allowed")
    next_performed = bool_value(data, "next_phase_unlock_performed", "no_submit_approval_ledger.next_phase_unlock_performed")
    transition_allowed = bool_value(data, "transition_to_next_phase_allowed", "no_submit_approval_ledger.transition_to_next_phase_allowed")
    transition_performed = bool_value(data, "transition_to_next_phase_performed", "no_submit_approval_ledger.transition_to_next_phase_performed")
    submit_relaxed = bool_value(data, "submit_boundary_relaxed", "no_submit_approval_ledger.submit_boundary_relaxed")
    approval_performed = bool_value(data, "approval_performed", "no_submit_approval_ledger.approval_performed")
    safety_ok = all(false_or_missing(data, path) for path in SAFETY_FALSE_PATHS)

    complete = bool(
        status == "READY"
        and decision == SOURCE_34F_DECISION
        and source_34e_complete
        and schema_complete
        and sig_required
        and not sig_present
        and not sig_valid
        and digest_complete
        and not digest_match
        and approval_complete
        and approval_ready
        and unlock_locked
        and not next_allowed
        and not next_performed
        and not transition_allowed
        and not transition_performed
        and not submit_relaxed
        and not approval_performed
        and safety_ok
    )

    return Source34FOperatorSignatureValidation(
        complete=complete, report=rel, status=status or None, decision=decision or None,
        error=None if complete else "source_34f_gate_not_complete",
        source_34e_complete=source_34e_complete,
        signature_file_schema_ledger_complete=schema_complete,
        signature_file_required=sig_required,
        signature_file_present=sig_present,
        signature_file_valid=sig_valid,
        eligibility_matrix_digest_match_complete=digest_complete,
        eligibility_matrix_digest_match=digest_match,
        no_submit_approval_ledger_complete=approval_complete,
        no_submit_approval_ready=approval_ready,
        unlock_boundary_locked=unlock_locked,
        next_phase_unlock_allowed=next_allowed,
        next_phase_unlock_performed=next_performed,
        transition_to_next_phase_allowed=transition_allowed,
        transition_to_next_phase_performed=transition_performed,
        submit_boundary_relaxed=submit_relaxed,
        approval_performed=approval_performed,
        expected_eligibility_matrix_digest=str_or_none(data, "expected_eligibility_matrix_digest", "eligibility_matrix_digest_match.expected_eligibility_matrix_digest"),
        provided_eligibility_matrix_digest=str_or_none(data, "provided_eligibility_matrix_digest", "eligibility_matrix_digest_match.provided_eligibility_matrix_digest"),
        eligibility_matrix_freeze_digest=str_or_none(data, "eligibility_matrix_freeze_digest"),
        no_submit_handoff_digest=str_or_none(data, "no_submit_handoff_digest"),
        no_submit_approval_digest=str_or_none(data, "no_submit_approval_digest"),
        signature_file_schema_digest=str_or_none(data, "signature_file_schema_digest"),
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
    )


def build_operator_signature_example(source: Source34FOperatorSignatureValidation) -> OperatorSignatureExampleLedger:
    required_fields = [
        "schema_version", "operator_id", "operator_statement", "source_34f_report",
        "expected_eligibility_matrix_digest", "no_submit_handoff_digest", "no_submit_acknowledgement",
        "transition_unlock_requested", "exchange_submit_requested", "utc_signed_at", "signature_token_sha256",
    ]
    example = {
        "schema_version": "4B436634G.operator_signature_example.v1",
        "operator_id": "<operator-id>",
        "operator_statement": "I reviewed 34B-34F evidence and acknowledge this example is not an approval token.",
        "source_34f_report": source.report,
        "expected_eligibility_matrix_digest": source.expected_eligibility_matrix_digest,
        "no_submit_handoff_digest": source.no_submit_handoff_digest,
        "no_submit_acknowledgement": True,
        "transition_unlock_requested": False,
        "exchange_submit_requested": False,
        "utc_signed_at": "<YYYY-MM-DDTHH:MM:SSZ>",
        "signature_token_sha256": "<sha256-of-offline-human-token>",
        "not_an_approval": True,
        "dry_run_only": True,
    }
    payload = {"required_fields": required_fields, "example_signature_payload": example, "real_operator_signature_present": False}
    return OperatorSignatureExampleLedger(
        complete=True,
        example_status="OPERATOR_SIGNATURE_EXAMPLE_READY_NOT_AN_APPROVAL",
        real_operator_signature_present=False,
        example_is_not_approval=True,
        signature_file_schema_version="4B436634G.operator_signature_example.v1",
        required_signature_fields=required_fields,
        example_signature_payload=example,
        digest=stable_json_digest(payload),
    )


def build_approval_simulation_dry_run(source: Source34FOperatorSignatureValidation, example: OperatorSignatureExampleLedger) -> ApprovalSimulationDryRunLedger:
    criteria = [
        {"name": "source_34f_complete", "accepted": source.complete},
        {"name": "operator_signature_example_complete", "accepted": example.complete},
        {"name": "example_is_not_approval", "accepted": example.example_is_not_approval},
        {"name": "real_operator_signature_absent", "accepted": not example.real_operator_signature_present},
        {"name": "approval_not_performed", "accepted": True},
        {"name": "transition_not_allowed", "accepted": True},
        {"name": "next_phase_unlock_not_allowed", "accepted": True},
    ]
    rejected = [item for item in criteria if not item["accepted"]]
    payload = {"criteria": criteria, "source_34f_report": source.report, "example_digest": example.digest}
    return ApprovalSimulationDryRunLedger(
        complete=len(rejected) == 0,
        simulation_status="APPROVAL_SIMULATION_DRY_RUN_HOLD_NO_REAL_SIGNATURE" if len(rejected) == 0 else "APPROVAL_SIMULATION_DRY_RUN_BLOCKED",
        simulation_dry_run_only=True,
        real_operator_signature_present=False,
        simulated_signature_schema_valid=True,
        simulated_digest_match=False,
        simulated_approval_performed=False,
        transition_to_next_phase_allowed=False,
        transition_to_next_phase_performed=False,
        next_phase_unlock_allowed=False,
        next_phase_unlock_performed=False,
        accepted_simulation_criterion_count=len(criteria) - len(rejected),
        rejected_simulation_criterion_count=len(rejected),
        criteria=criteria,
        digest=stable_json_digest(payload),
    )


def build_final_no_submit_governance_ledger(simulation: ApprovalSimulationDryRunLedger) -> FinalNoSubmitGovernanceLedger:
    payload = {"simulation_digest": simulation.digest, "next_phase": NEXT_PHASE, "governance_locked": True}
    return FinalNoSubmitGovernanceLedger(
        complete=simulation.complete,
        governance_status="FINAL_NO_SUBMIT_GOVERNANCE_LEDGER_LOCKED" if simulation.complete else "FINAL_NO_SUBMIT_GOVERNANCE_LEDGER_BLOCKED",
        governance_locked=True,
        approval_performed=False,
        simulated_approval_performed=False,
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


def build_report(repo_root: Path, reports_dir: Path | None = None, write_files: bool = False) -> SignatureApprovalPackageReport:
    reports_base = reports_dir if reports_dir is not None else repo_root / "reports" / "recovery"
    source = parse_source_34f(repo_root)
    example = build_operator_signature_example(source)
    simulation = build_approval_simulation_dry_run(source, example)
    governance = build_final_no_submit_governance_ledger(simulation)

    ok = bool(source.complete and example.complete and simulation.complete and governance.complete and governance.governance_locked)
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    example_path = simulation_path = governance_path = report_path = None
    if write_files:
        reports_base.mkdir(parents=True, exist_ok=True)
        stamp = utc_timestamp()
        example_file = reports_base / f"{PATCH_ID}_operator_signature_example_{stamp}.json"
        simulation_file = reports_base / f"{PATCH_ID}_approval_simulation_dry_run_{stamp}.json"
        governance_file = reports_base / f"{PATCH_ID}_final_no_submit_governance_ledger_{stamp}.json"
        suffix = "ready" if ok else "not_ready"
        main_file = reports_base / f"{PATCH_ID}_signature_approval_package_{stamp}_{suffix}.json"
        example_file.write_text(json.dumps(asdict(example), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        simulation_file.write_text(json.dumps(asdict(simulation), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        governance_file.write_text(json.dumps(asdict(governance), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        example_path = relative_to_repo(repo_root, example_file)
        simulation_path = relative_to_repo(repo_root, simulation_file)
        governance_path = relative_to_repo(repo_root, governance_file)
        report_path = relative_to_repo(repo_root, main_file)

    report = SignatureApprovalPackageReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        check_name="signature_approval_package",
        status=status,
        ok=ok,
        decision=decision,
        source_34f_complete=source.complete,
        source_34f_report=source.report,
        source_34f_decision=source.decision,
        operator_signature_example_complete=example.complete,
        operator_signature_example_status=example.example_status,
        real_operator_signature_present=example.real_operator_signature_present,
        example_is_not_approval=example.example_is_not_approval,
        approval_simulation_dry_run_complete=simulation.complete,
        approval_simulation_status=simulation.simulation_status,
        simulated_signature_schema_valid=simulation.simulated_signature_schema_valid,
        simulated_digest_match=simulation.simulated_digest_match,
        simulated_approval_performed=simulation.simulated_approval_performed,
        final_no_submit_governance_ledger_complete=governance.complete,
        final_no_submit_governance_status=governance.governance_status,
        governance_locked=governance.governance_locked,
        approval_performed=governance.approval_performed,
        signature_file_required=source.signature_file_required,
        signature_file_present=source.signature_file_present,
        signature_file_valid=source.signature_file_valid,
        eligibility_matrix_digest_match=source.eligibility_matrix_digest_match,
        no_submit_approval_ready=source.no_submit_approval_ready,
        unlock_boundary_locked=source.unlock_boundary_locked,
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
        expected_eligibility_matrix_digest=source.expected_eligibility_matrix_digest,
        provided_eligibility_matrix_digest=source.provided_eligibility_matrix_digest,
        eligibility_matrix_freeze_digest=source.eligibility_matrix_freeze_digest,
        no_submit_handoff_digest=source.no_submit_handoff_digest,
        no_submit_approval_digest=source.no_submit_approval_digest,
        signature_file_schema_digest=source.signature_file_schema_digest,
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
        operator_signature_example_digest=example.digest,
        approval_simulation_digest=simulation.digest,
        final_no_submit_governance_digest=governance.digest,
        report_path=report_path,
        operator_signature_example_path=example_path,
        approval_simulation_dry_run_path=simulation_path,
        final_no_submit_governance_ledger_path=governance_path,
    )

    if write_files and report_path is not None:
        main_file = repo_root / report_path
        main_file.write_text(json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
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
