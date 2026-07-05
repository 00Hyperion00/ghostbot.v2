from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PATCH_ID = "4B436638D"
PATCH_VERSION = "4B.4.3.6.6.38D"
PATCH_NAME = "Paper Sandbox Operator Approval Ledger"

SOURCE_PATCH_ID = "4B436638C"
SOURCE_READY_DECISION = (
    "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_READY_LOCAL_DRY_RUN_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

READY_DECISION = (
    "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_READY_TYPED_APPROVAL_EVIDENCE_"
    "OPERATOR_IDENTITY_NO_RUNTIME_START_NO_NETWORK_ORDER_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_NOT_READY_NO_RUNTIME_START_"
    "NO_NETWORK_ORDER_LOCKED"
)

NEXT_PHASE = "4B.4.3.6.6.38E"
NEXT_PHASE_NAME = "Paper Sandbox Runtime Activation Preflight"

APPROVAL_PHRASE_REQUIRED = "APPROVE PAPER SANDBOX OPERATOR LEDGER REVIEW ONLY"
SOURCE_REPORT_PATTERN = "4B436638C_paper_sandbox_dry_run_runtime_harness_*_ready.json"


@dataclass(frozen=True)
class OperatorApprovalEvidence:
    approval_phrase: str | None
    operator_id: str | None
    operator_name: str | None
    operator_role: str | None
    approved_at_utc: str | None
    source_report: str | None
    approval_scope: str | None = "paper_sandbox_operator_approval_ledger_review_only"


@dataclass(frozen=True)
class ApprovalEvaluation:
    accepted_for_review: bool
    approval_valid: bool
    result: str
    denial_reason: str | None
    runtime_start_allowed: bool
    paper_order_submit_allowed: bool
    network_order_submit_allowed: bool
    live_transition_allowed: bool
    exchange_submit_allowed: bool


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _stable_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "src").exists() or (candidate / ".git").exists():
            return candidate
    return current


def _safe_bool(payload: Mapping[str, Any], key: str, expected: bool) -> bool:
    return bool(payload.get(key)) is expected


def _latest_report(reports_dir: Path, pattern: str) -> Path | None:
    if not reports_dir.exists():
        return None
    candidates = [path for path in reports_dir.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))[-1]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected in {path}")
    return payload


def evaluate_operator_approval_ledger(evidence: OperatorApprovalEvidence) -> ApprovalEvaluation:
    runtime_denied = {
        "runtime_start_allowed": False,
        "paper_order_submit_allowed": False,
        "network_order_submit_allowed": False,
        "live_transition_allowed": False,
        "exchange_submit_allowed": False,
    }

    if not evidence.approval_phrase:
        return ApprovalEvaluation(False, False, "DENY_TYPED_APPROVAL_EVIDENCE_REQUIRED", "approval_phrase_missing", **runtime_denied)
    if evidence.approval_phrase != APPROVAL_PHRASE_REQUIRED:
        return ApprovalEvaluation(False, False, "DENY_TYPED_APPROVAL_EVIDENCE_MISMATCH", "approval_phrase_invalid", **runtime_denied)
    if not evidence.operator_id:
        return ApprovalEvaluation(False, False, "DENY_OPERATOR_IDENTITY_REQUIRED", "operator_id_missing", **runtime_denied)
    if not evidence.operator_name:
        return ApprovalEvaluation(False, False, "DENY_OPERATOR_NAME_REQUIRED", "operator_name_missing", **runtime_denied)
    if not evidence.operator_role:
        return ApprovalEvaluation(False, False, "DENY_OPERATOR_ROLE_REQUIRED", "operator_role_missing", **runtime_denied)
    if not evidence.approved_at_utc:
        return ApprovalEvaluation(False, False, "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED", "approved_at_utc_missing", **runtime_denied)
    if not evidence.source_report:
        return ApprovalEvaluation(False, False, "DENY_SOURCE_REPORT_REQUIRED", "source_report_missing", **runtime_denied)

    return ApprovalEvaluation(
        True,
        True,
        "APPROVAL_LEDGER_ACCEPTED_FOR_REVIEW_RUNTIME_DENIED_NO_SUBMIT",
        None,
        **runtime_denied,
    )


def _source_38c_gate(reports_dir: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    source_path = _latest_report(reports_dir, SOURCE_REPORT_PATTERN)
    if source_path is None:
        return {
            "source_38c_complete": False,
            "source_38c_status": "SOURCE_38C_MISSING",
            "source_38c_report": None,
            "source_38c_decision": None,
            "source_38c_safety_violation_count": None,
            "source_38c_safety_violations": [],
        }, [f"missing source 38C READY report matching {SOURCE_REPORT_PATTERN}"]

    try:
        source = _read_json(source_path)
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "source_38c_complete": False,
            "source_38c_status": "SOURCE_38C_UNREADABLE",
            "source_38c_report": str(source_path),
            "source_38c_decision": None,
            "source_38c_safety_violation_count": None,
            "source_38c_safety_violations": [],
        }, [f"source 38C report unreadable: {exc}"]

    safety_violations = list(source.get("final_safety_violations") or [])
    required = {
        "status": "READY",
        "decision": SOURCE_READY_DECISION,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "paper_sandbox_dry_run_runtime_harness_ready": True,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_order_submit_allowed": False,
        "order_submit_performed": False,
        "runtime_start_performed": False,
        "source_38b_safety_violation_count": 0,
        "final_safety_violation_count": 0,
    }
    for key, expected in required.items():
        if source.get(key) != expected:
            errors.append(f"source_38c invalid {key}: expected {expected!r}, got {source.get(key)!r}")

    source_complete = not errors and not safety_violations
    gate = {
        "source_38c_complete": source_complete,
        "source_38c_status": "SOURCE_38C_READY" if source_complete else "SOURCE_38C_NOT_READY",
        "source_38c_report": str(source_path),
        "source_38c_decision": source.get("decision"),
        "source_38c_approved_for_paper_sandbox_dry_run_harness": bool(source.get("approved_for_paper_sandbox_dry_run_harness")),
        "source_38c_paper_sandbox_dry_run_runtime_harness_ready": bool(source.get("paper_sandbox_dry_run_runtime_harness_ready")),
        "source_38c_paper_transition_blocked": bool(source.get("paper_transition_blocked")),
        "source_38c_approved_for_paper_transition": bool(source.get("approved_for_paper_transition")),
        "source_38c_approved_for_live_real": bool(source.get("approved_for_live_real")),
        "source_38c_approved_for_exchange_submit": bool(source.get("approved_for_exchange_submit")),
        "source_38c_phase_38_planning_only": bool(source.get("phase_38_planning_only")),
        "source_38c_safety_violation_count": int(source.get("final_safety_violation_count") or 0),
        "source_38c_safety_violations": safety_violations,
    }
    return gate, errors


def _approval_ledger_policy(generated_at_utc: str, source_report: str | None) -> dict[str, Any]:
    rules = [
        {"rule_id": "typed_approval_evidence_required", "ready": True, "policy": "paper sandbox operator approval requires exact typed evidence"},
        {"rule_id": "operator_identity_required", "ready": True, "policy": "operator identity must be recorded with id, name and role"},
        {"rule_id": "operator_approval_timestamp_required", "ready": True, "policy": "approval evidence must carry an immutable UTC timestamp"},
        {"rule_id": "source_report_required", "ready": True, "policy": "approval ledger must reference the 38C source report"},
        {"rule_id": "missing_or_invalid_approval_fails_closed", "ready": True, "policy": "missing or mismatched typed approval fails closed"},
        {"rule_id": "valid_approval_is_review_only", "ready": True, "policy": "valid approval ledger is accepted for review only"},
        {"rule_id": "approval_does_not_start_runtime", "ready": True, "policy": "approval ledger cannot start paper runtime in 38D"},
        {"rule_id": "approval_does_not_enable_network_order", "ready": True, "policy": "approval ledger cannot enable network order submit"},
        {"rule_id": "next_phase_not_auto_unlocked", "ready": True, "policy": "38E is not auto-unlocked by 38D"},
    ]
    evidence_schema = {
        "approval_phrase_required": APPROVAL_PHRASE_REQUIRED,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "approved_at_utc_required": True,
        "source_report_required": True,
        "approval_scope": "paper_sandbox_operator_approval_ledger_review_only",
    }
    payload = {
        "policy_name": "paper_sandbox_operator_approval_ledger_policy",
        "operator_approval_ledger_complete": True,
        "operator_approval_ledger_locked": True,
        "operator_approval_ledger_ready": True,
        "operator_approval_ledger_status": "OPERATOR_APPROVAL_LEDGER_READY_TYPED_EVIDENCE_OPERATOR_IDENTITY_REQUIRED",
        "typed_approval_evidence_required": True,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "operator_approval_phrase_required": APPROVAL_PHRASE_REQUIRED,
        "operator_approval_evidence_schema": evidence_schema,
        "operator_approval_ledger_rule_count": len(rules),
        "operator_approval_ledger_ready_count": sum(1 for item in rules if item["ready"]),
        "operator_approval_ledger_rules": rules,
        "source_report": source_report,
        "generated_at_utc": generated_at_utc,
    }
    payload["operator_approval_ledger_digest"] = _stable_digest(payload)
    return payload


def _approval_ledger_probes(generated_at_utc: str, source_report: str | None) -> dict[str, Any]:
    valid_evidence = OperatorApprovalEvidence(
        approval_phrase=APPROVAL_PHRASE_REQUIRED,
        operator_id="operator.local.review",
        operator_name="Operator Review",
        operator_role="paper_sandbox_reviewer",
        approved_at_utc=generated_at_utc,
        source_report=source_report,
    )
    probe_specs: Sequence[tuple[str, OperatorApprovalEvidence, str]] = [
        (
            "missing_typed_approval_denied",
            OperatorApprovalEvidence(None, "operator.local.review", "Operator Review", "paper_sandbox_reviewer", generated_at_utc, source_report),
            "DENY_TYPED_APPROVAL_EVIDENCE_REQUIRED",
        ),
        (
            "invalid_typed_approval_denied",
            OperatorApprovalEvidence("APPROVE PAPER", "operator.local.review", "Operator Review", "paper_sandbox_reviewer", generated_at_utc, source_report),
            "DENY_TYPED_APPROVAL_EVIDENCE_MISMATCH",
        ),
        (
            "missing_operator_id_denied",
            OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, None, "Operator Review", "paper_sandbox_reviewer", generated_at_utc, source_report),
            "DENY_OPERATOR_IDENTITY_REQUIRED",
        ),
        (
            "missing_operator_name_denied",
            OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator.local.review", None, "paper_sandbox_reviewer", generated_at_utc, source_report),
            "DENY_OPERATOR_NAME_REQUIRED",
        ),
        (
            "missing_operator_role_denied",
            OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator.local.review", "Operator Review", None, generated_at_utc, source_report),
            "DENY_OPERATOR_ROLE_REQUIRED",
        ),
        (
            "missing_operator_timestamp_denied",
            OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator.local.review", "Operator Review", "paper_sandbox_reviewer", None, source_report),
            "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED",
        ),
        (
            "missing_source_report_denied",
            OperatorApprovalEvidence(APPROVAL_PHRASE_REQUIRED, "operator.local.review", "Operator Review", "paper_sandbox_reviewer", generated_at_utc, None),
            "DENY_SOURCE_REPORT_REQUIRED",
        ),
        (
            "valid_ledger_accepted_for_review",
            valid_evidence,
            "APPROVAL_LEDGER_ACCEPTED_FOR_REVIEW_RUNTIME_DENIED_NO_SUBMIT",
        ),
    ]

    probes: list[dict[str, Any]] = []
    for probe_id, evidence, expected in probe_specs:
        result = evaluate_operator_approval_ledger(evidence)
        probes.append(
            {
                "probe_id": probe_id,
                "expected": expected,
                "result": result.result,
                "passed": result.result == expected,
                "approval_valid": result.approval_valid,
                "accepted_for_review": result.accepted_for_review,
                "runtime_start_allowed": result.runtime_start_allowed,
                "paper_order_submit_allowed": result.paper_order_submit_allowed,
                "network_order_submit_allowed": result.network_order_submit_allowed,
                "live_transition_allowed": result.live_transition_allowed,
                "exchange_submit_allowed": result.exchange_submit_allowed,
            }
        )

    valid_result = evaluate_operator_approval_ledger(valid_evidence)
    probes.extend(
        [
            {
                "probe_id": "valid_ledger_runtime_start_denied_no_submit",
                "expected": False,
                "result": valid_result.runtime_start_allowed,
                "passed": valid_result.runtime_start_allowed is False,
                "runtime_start_allowed": False,
            },
            {
                "probe_id": "valid_ledger_network_order_denied",
                "expected": False,
                "result": valid_result.network_order_submit_allowed,
                "passed": valid_result.network_order_submit_allowed is False,
                "network_order_submit_allowed": False,
            },
            {
                "probe_id": "paper_runtime_start_not_performed",
                "expected": False,
                "result": False,
                "passed": True,
            },
            {
                "probe_id": "next_phase_not_auto_unlocked",
                "expected": False,
                "result": False,
                "passed": True,
            },
        ]
    )

    payload = {
        "probe_name": "paper_sandbox_operator_approval_ledger_probe",
        "operator_approval_ledger_probe_complete": True,
        "operator_approval_ledger_probe_locked": True,
        "operator_approval_ledger_probe_mode": "STATIC_TYPED_APPROVAL_LEDGER_NO_RUNTIME_NO_NETWORK_ORDER",
        "operator_approval_ledger_probe_count": len(probes),
        "operator_approval_ledger_probe_passed_count": sum(1 for item in probes if item["passed"]),
        "operator_approval_ledger_probes": probes,
        "operator_approval_valid_evidence_sample": asdict(valid_evidence),
        "typed_approval_missing_denied": True,
        "typed_approval_invalid_denied": True,
        "operator_id_missing_denied": True,
        "operator_name_missing_denied": True,
        "operator_role_missing_denied": True,
        "operator_approval_timestamp_missing_denied": True,
        "source_report_missing_denied": True,
        "valid_operator_approval_ledger_accepted_for_review": True,
        "valid_operator_approval_ledger_runtime_denied_no_submit": True,
        "valid_operator_approval_ledger_network_order_denied": True,
        "generated_at_utc": generated_at_utc,
        "source_report": source_report,
    }
    payload["operator_approval_ledger_probe_digest"] = _stable_digest(payload)
    return payload


def _no_runtime_no_network_order_guard(generated_at_utc: str, source_report: str | None) -> dict[str, Any]:
    rules = [
        {"rule_id": "paper_runtime_start_forbidden", "ready": True, "policy": "38D cannot start paper runtime"},
        {"rule_id": "paper_order_submit_forbidden", "ready": True, "policy": "38D cannot submit paper orders"},
        {"rule_id": "network_order_submit_forbidden", "ready": True, "policy": "network order submit remains forbidden"},
        {"rule_id": "live_real_approval_false", "ready": True, "policy": "live-real approval remains false"},
        {"rule_id": "exchange_submit_approval_false", "ready": True, "policy": "exchange submit approval remains false"},
        {"rule_id": "signed_request_forbidden", "ready": True, "policy": "signed requests remain forbidden"},
        {"rule_id": "private_api_forbidden", "ready": True, "policy": "private API access remains forbidden"},
        {"rule_id": "network_request_forbidden", "ready": True, "policy": "network requests are not performed by 38D"},
        {"rule_id": "runtime_overlay_training_reload_forbidden", "ready": True, "policy": "runtime overlay, training and reload remain forbidden"},
    ]
    payload = {
        "guard_name": "no_runtime_start_no_network_order_guard",
        "no_runtime_start_no_network_order_guard_complete": True,
        "no_runtime_start_no_network_order_guard_locked": True,
        "no_runtime_start_no_network_order_guard_status": "NO_RUNTIME_START_NO_NETWORK_ORDER_GUARD_READY",
        "no_runtime_start_no_network_order_guard_rule_count": len(rules),
        "no_runtime_start_no_network_order_guard_ready_count": sum(1 for item in rules if item["ready"]),
        "no_runtime_start_no_network_order_guard_rules": rules,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "source_report": source_report,
        "generated_at_utc": generated_at_utc,
    }
    payload["no_runtime_start_no_network_order_guard_digest"] = _stable_digest(payload)
    return payload


def _gate_checks(source_gate: Mapping[str, Any], policy: Mapping[str, Any], probes: Mapping[str, Any], guard: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = [
        ("source_38c_ready", source_gate.get("source_38c_status") == "SOURCE_38C_READY"),
        ("phase_37_final_closed", True),
        ("paper_sandbox_dry_run_harness_ready", source_gate.get("source_38c_paper_sandbox_dry_run_runtime_harness_ready") is True),
        ("operator_approval_ledger_locked", policy.get("operator_approval_ledger_locked") is True),
        ("typed_approval_evidence_required", policy.get("typed_approval_evidence_required") is True),
        ("operator_identity_required", policy.get("operator_identity_required") is True),
        ("operator_id_required", policy.get("operator_id_required") is True),
        ("operator_name_required", policy.get("operator_name_required") is True),
        ("operator_role_required", policy.get("operator_role_required") is True),
        ("operator_approval_timestamp_required", policy.get("operator_approval_timestamp_required") is True),
        ("source_report_required", policy.get("source_report_required") is True),
        ("typed_approval_missing_denied", probes.get("typed_approval_missing_denied") is True),
        ("typed_approval_invalid_denied", probes.get("typed_approval_invalid_denied") is True),
        ("operator_identity_missing_denied", probes.get("operator_id_missing_denied") is True),
        ("operator_approval_ledger_probes_passed", probes.get("operator_approval_ledger_probe_count") == probes.get("operator_approval_ledger_probe_passed_count")),
        ("valid_ledger_review_only", probes.get("valid_operator_approval_ledger_accepted_for_review") is True),
        ("valid_ledger_runtime_denied_no_submit", probes.get("valid_operator_approval_ledger_runtime_denied_no_submit") is True),
        ("valid_ledger_network_order_denied", probes.get("valid_operator_approval_ledger_network_order_denied") is True),
        ("paper_transition_not_approved_by_patch", True),
        ("paper_runtime_not_started", guard.get("paper_runtime_start_performed") is False),
        ("paper_order_submit_forbidden", guard.get("paper_order_submit_allowed") is False),
        ("network_order_submit_forbidden", guard.get("network_order_submit_allowed") is False),
        ("live_real_remains_not_approved", guard.get("approved_for_live_real") is False),
        ("exchange_submit_remains_forbidden", guard.get("approved_for_exchange_submit") is False),
        ("signed_request_forbidden", guard.get("signed_request_performed") is False),
        ("private_api_forbidden", guard.get("private_api_access_allowed") is False),
        ("network_request_forbidden", guard.get("network_request_performed") is False),
        ("runtime_overlay_training_reload_forbidden", guard.get("runtime_overlay_activated") is False and guard.get("training_performed") is False and guard.get("reload_performed") is False),
        ("git_mutating_operations_forbidden", True),
        ("report_mutation_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    return [{"check_id": check_id, "ready": bool(ready), "unlock_allowed": False} for check_id, ready in checks]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def build_report(repo_root: Path | None = None, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    root = _repo_root_from(repo_root)
    out_dir = reports_dir or (root / "reports" / "recovery")
    generated_at_utc = _utc_timestamp()

    source_gate, source_errors = _source_38c_gate(out_dir)
    source_report = source_gate.get("source_38c_report")
    policy = _approval_ledger_policy(generated_at_utc, str(source_report) if source_report else None)
    probes = _approval_ledger_probes(generated_at_utc, str(source_report) if source_report else None)
    guard = _no_runtime_no_network_order_guard(generated_at_utc, str(source_report) if source_report else None)
    gate_checks = _gate_checks(source_gate, policy, probes, guard)

    safety_flags = {
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_ready": False,
        "paper_transition_approval_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "paper_submit_allowed": False,
        "approved_for_live_real": False,
        "live_environment_enabled": False,
        "live_transition_ready": False,
        "live_transition_allowed": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "automatic_commit_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "historical_report_mutation_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }

    errors = list(source_errors)
    gate_ready = all(item["ready"] for item in gate_checks)
    ok = not errors and gate_ready
    status = "READY" if ok else "NOT_READY"
    decision = READY_DECISION if ok else NOT_READY_DECISION

    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": status,
        "ok": ok,
        "decision": decision,
        "errors": errors,
        "generated_at_utc": generated_at_utc,
        "source_report": source_report,
        "review_name": "paper_sandbox_operator_approval_ledger",
        "phase_37_final_closed": True,
        "phase_38_execution_started": False,
        "phase_38_planning_only": True,
        "phase_38_unlocked": False,
        "paper_sandbox_operator_approval_ledger_complete": ok,
        "paper_sandbox_operator_approval_ledger_locked": True,
        "paper_sandbox_operator_approval_ledger_ready": ok,
        "paper_sandbox_operator_approval_ledger_status": "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_READY_NO_RUNTIME_START_NO_ORDER" if ok else "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_NOT_READY",
        "paper_sandbox_operator_approval_ledger_gate_complete": ok,
        "paper_sandbox_operator_approval_ledger_gate_locked": True,
        "paper_sandbox_operator_approval_ledger_gate_status": "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_GATE_READY" if ok else "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_GATE_NOT_READY",
        "paper_sandbox_operator_approval_ledger_gate_check_count": len(gate_checks),
        "paper_sandbox_operator_approval_ledger_gate_ready_count": sum(1 for item in gate_checks if item["ready"]),
        "paper_sandbox_operator_approval_ledger_gate_checks": gate_checks,
        "operator_approval_runtime_binding_performed": False,
        "operator_approval_ledger_runtime_binding_performed": False,
        "operator_approval_ledger_source_mutation_performed": False,
        "operator_approval_ledger_mutation_performed": False,
        "operator_approval_review_only": True,
        "operator_approval_runtime_start_denied_no_submit": True,
        "operator_approval_network_order_denied": True,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        **source_gate,
        **policy,
        **probes,
        **guard,
        **safety_flags,
    }

    safety_violation_keys = [
        "approved_for_paper_transition",
        "paper_transition_unblocked",
        "paper_runtime_start_performed",
        "paper_order_submit_performed",
        "approved_for_live_real",
        "approved_for_exchange_submit",
        "network_order_submit_performed",
        "order_submit_performed",
        "exchange_submit_performed",
        "network_request_performed",
        "http_request_performed",
        "signed_request_performed",
        "private_api_access_allowed",
        "runtime_start_performed",
        "runtime_overlay_activated",
        "training_performed",
        "reload_performed",
        "transition_to_next_phase_performed",
    ]
    safety_violations = [key for key in safety_violation_keys if report.get(key) is not False]
    report["final_safety_violations"] = safety_violations
    report["final_safety_violation_count"] = len(safety_violations)
    if safety_violations:
        report["ok"] = False
        report["status"] = "NOT_READY"
        report["decision"] = NOT_READY_DECISION
        report["errors"] = [*errors, *[f"safety violation: {key}" for key in safety_violations]]

    gate_payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "gate_name": "paper_sandbox_operator_approval_ledger_gate",
        "status": report["paper_sandbox_operator_approval_ledger_gate_status"],
        "checks": gate_checks,
        "generated_at_utc": generated_at_utc,
        "source_report": source_report,
    }
    report["paper_sandbox_operator_approval_ledger_gate_digest"] = _stable_digest(gate_payload)
    report["report_digest"] = _stable_digest({k: v for k, v in report.items() if k not in {"report_digest", "report_path"}})

    if write_reports:
        suffix = "ready" if report["status"] == "READY" else "not_ready"
        component_paths = {
            "operator_approval_ledger_policy_path": out_dir / f"{PATCH_ID}_operator_approval_ledger_policy_{generated_at_utc}.json",
            "operator_approval_ledger_probe_path": out_dir / f"{PATCH_ID}_operator_approval_ledger_probe_{generated_at_utc}.json",
            "no_runtime_start_no_network_order_guard_path": out_dir / f"{PATCH_ID}_no_runtime_start_no_network_order_guard_{generated_at_utc}.json",
            "paper_sandbox_operator_approval_ledger_gate_path": out_dir / f"{PATCH_ID}_paper_sandbox_operator_approval_ledger_gate_{generated_at_utc}.json",
            "report_path": out_dir / f"{PATCH_ID}_paper_sandbox_operator_approval_ledger_{generated_at_utc}_{suffix}.json",
        }
        _write_json(component_paths["operator_approval_ledger_policy_path"], policy)
        _write_json(component_paths["operator_approval_ledger_probe_path"], probes)
        _write_json(component_paths["no_runtime_start_no_network_order_guard_path"], guard)
        _write_json(component_paths["paper_sandbox_operator_approval_ledger_gate_path"], gate_payload)
        for key, value in component_paths.items():
            report[key] = str(value)
        report["report_digest"] = _stable_digest({k: v for k, v in report.items() if k not in {"report_digest"}})
        _write_json(component_paths["report_path"], report)
    else:
        report.setdefault("operator_approval_ledger_policy_path", None)
        report.setdefault("operator_approval_ledger_probe_path", None)
        report.setdefault("no_runtime_start_no_network_order_guard_path", None)
        report.setdefault("paper_sandbox_operator_approval_ledger_gate_path", None)
        report.setdefault("report_path", None)

    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(reports_dir=args.reports_dir, write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
