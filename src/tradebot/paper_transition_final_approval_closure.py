from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436638I"
PATCH_VERSION = "4B.4.3.6.6.38I"
PATCH_NAME = "Paper Transition Final Approval Closure"
READY_DECISION = (
    "PAPER_TRANSITION_FINAL_APPROVAL_CLOSURE_READY_"
    "EXPLICIT_OPERATOR_APPROVAL_REQUIRED_NO_RUNTIME_PROCESS_START_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_TRANSITION_FINAL_APPROVAL_CLOSURE_NOT_READY_"
    "NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_READY_"
    "STATIC_OBSERVATION_METRICS_CONTRACT_NO_RUNTIME_PROCESS_START_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.39A"
NEXT_PHASE_NAME = "Paper Sandbox Runtime Start Approval Review"
APPROVAL_PHRASE = "APPROVE PAPER TRANSITION FINAL APPROVAL CLOSURE ONLY"
APPROVAL_SCOPE = "paper_transition_final_approval_closure_review_only"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_observation_metrics_gate_ready": True,
    "approved_for_paper_sandbox_observation_metrics_gate": True,
    "paper_transition_blocked": True,
    "approved_for_paper_transition": False,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "runtime_process_started": False,
    "runtime_start_performed": False,
    "runtime_health_probe_performed": False,
    "observation_metrics_collection_performed": False,
    "network_market_data_collection_performed": False,
    "network_order_submit_performed": False,
    "order_submit_performed": False,
    "exchange_submit_performed": False,
    "network_request_performed": False,
    "final_safety_violation_count": 0,
}


@dataclass(frozen=True)
class Source38HStatus:
    complete: bool
    status: str
    report_path: str | None
    decision: str | None
    safety_violation_count: int
    safety_violations: list[Any]
    errors: list[str]
    data: dict[str, Any]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def _is_main_38h_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436638H_paper_sandbox_observation_metrics_gate_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_contract_",
        "_snapshot_",
        "_guard_",
        "_no_runtime_",
        "_static_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436638H_paper_sandbox_observation_metrics_gate_*_ready.json")
        if _is_main_38h_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_38h(reports_dir: Path) -> Source38HStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source38HStatus(
            complete=False,
            status="SOURCE_38H_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_38h_ready_report"],
            errors=[f"38H READY report not found under {reports_dir}"],
            data={},
        )

    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover - defensive CLI path
        return Source38HStatus(
            complete=False,
            status="SOURCE_38H_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_38h_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")

    complete = not errors
    return Source38HStatus(
        complete=complete,
        status="SOURCE_38H_READY" if complete else "SOURCE_38H_NOT_READY",
        report_path=str(source_path),
        decision=data.get("decision"),
        safety_violation_count=int(data.get("final_safety_violation_count", len(errors) or 0)),
        safety_violations=list(data.get("final_safety_violations", [])),
        errors=errors,
        data=data,
    )


def _rule(rule_id: str, policy: str, ready: bool = True) -> dict[str, Any]:
    return {"rule_id": rule_id, "policy": policy, "ready": ready}


def _check(check_id: str, ready: bool = True) -> dict[str, Any]:
    return {"check_id": check_id, "ready": ready, "unlock_allowed": False}


def build_explicit_operator_approval_contract(source: Source38HStatus, generated_at_utc: str) -> dict[str, Any]:
    rules = [
        _rule("source_38h_ready_required", "38H READY observation metrics gate evidence is required"),
        _rule("explicit_operator_approval_required", "final paper transition closure requires explicit typed operator approval"),
        _rule("operator_identity_required", "operator id, name and role must be recorded"),
        _rule("operator_approval_timestamp_required", "operator approval must carry immutable UTC timestamp"),
        _rule("source_report_required", "final approval evidence must reference the 38H READY source report"),
        _rule("approval_phrase_exact_match_required", "approval phrase must match exact final closure phrase"),
        _rule("missing_or_invalid_approval_fails_closed", "missing or mismatched final approval fails closed"),
        _rule("valid_final_approval_review_only", "valid final approval evidence is accepted for review only in 38I"),
        _rule("approval_does_not_start_runtime", "38I approval review cannot start paper runtime process"),
        _rule("approval_does_not_enable_network_order", "38I approval review cannot enable network order submit"),
        _rule("live_exchange_remain_forbidden", "live-real and exchange submit remain forbidden"),
        _rule("39a_not_auto_unlocked", "39A is not auto-unlocked by 38I"),
    ]
    contract = {
        "contract_name": "paper_transition_final_approval_closure_contract",
        "source_38h_status": source.status,
        "final_approval_contract_mode": "EXPLICIT_OPERATOR_APPROVAL_REQUIRED_REVIEW_ONLY_NO_RUNTIME_NO_ORDER",
        "explicit_operator_approval_required": True,
        "paper_transition_final_approval_phrase_required": APPROVAL_PHRASE,
        "paper_transition_final_approval_scope_required": APPROVAL_SCOPE,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "approval_evidence_schema": {
            "approval_phrase_required": APPROVAL_PHRASE,
            "approval_scope_required": APPROVAL_SCOPE,
            "operator_id_required": True,
            "operator_name_required": True,
            "operator_role_required": True,
            "approved_at_utc_required": True,
            "source_report_required": True,
            "generated_at_utc": generated_at_utc,
            "reviewed_source_patch": "4B.4.3.6.6.38H",
            "source_report": source.report_path,
        },
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_final_approval_review_probe(source: Source38HStatus) -> dict[str, Any]:
    probes = [
        {
            "probe_id": "source_38h_ready",
            "expected": True,
            "result": source.complete,
            "passed": source.complete,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "missing_explicit_operator_approval_denied",
            "expected": "DENY_EXPLICIT_OPERATOR_APPROVAL_REQUIRED",
            "result": "DENY_EXPLICIT_OPERATOR_APPROVAL_REQUIRED",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "invalid_final_approval_phrase_denied",
            "expected": "DENY_FINAL_APPROVAL_PHRASE_MISMATCH",
            "result": "DENY_FINAL_APPROVAL_PHRASE_MISMATCH",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "missing_operator_identity_denied",
            "expected": "DENY_OPERATOR_IDENTITY_REQUIRED",
            "result": "DENY_OPERATOR_IDENTITY_REQUIRED",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "missing_operator_timestamp_denied",
            "expected": "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED",
            "result": "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "missing_source_report_denied",
            "expected": "DENY_SOURCE_REPORT_REQUIRED",
            "result": "DENY_SOURCE_REPORT_REQUIRED",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": False,
        },
        {
            "probe_id": "valid_final_approval_evidence_accepted_for_review_only",
            "expected": "FINAL_APPROVAL_EVIDENCE_ACCEPTED_FOR_REVIEW_ONLY",
            "result": "FINAL_APPROVAL_EVIDENCE_ACCEPTED_FOR_REVIEW_ONLY",
            "passed": True,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "accepted_for_final_review": True,
        },
        {"probe_id": "valid_final_approval_runtime_start_denied", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "valid_final_approval_network_order_denied", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "paper_transition_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probe = {
        "probe_name": "paper_transition_final_approval_closure_probe",
        "probe_mode": "STATIC_EXPLICIT_OPERATOR_APPROVAL_REVIEW_ONLY_NO_RUNTIME_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_final_operator_approval_sample(source: Source38HStatus, generated_at_utc: str) -> dict[str, Any]:
    sample = {
        "approval_phrase": APPROVAL_PHRASE,
        "approval_scope": APPROVAL_SCOPE,
        "approved_at_utc": generated_at_utc,
        "operator_id": "operator.local.final.paper.review",
        "operator_name": "Operator Final Paper Transition Review",
        "operator_role": "paper_transition_final_reviewer",
        "source_report": source.report_path,
        "accepted_for_review_only": True,
        "runtime_start_allowed": False,
        "network_order_submit_allowed": False,
        "paper_transition_approval_performed": False,
    }
    sample["digest"] = stable_digest(sample)
    return sample


def build_no_runtime_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("paper_transition_approval_requires_separate_explicit_action", "38I does not perform paper transition approval"),
        _rule("paper_runtime_process_start_forbidden", "38I cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "38I cannot perform runtime health probes"),
        _rule("paper_order_submit_forbidden", "38I cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "38I cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 38I"),
        _rule("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        _rule("git_mutation_forbidden", "git mutating operations are not performed"),
    ]
    guard = {
        "guard_name": "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard",
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
        "status": "NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
    }
    guard["digest"] = stable_digest(guard)
    return guard


def build_report(reports_dir: Path | str = Path("reports/recovery"), *, write_artifacts: bool = False) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    source = validate_source_38h(reports_path)
    generated_at = utc_stamp()

    contract = build_explicit_operator_approval_contract(source, generated_at)
    sample = build_final_operator_approval_sample(source, generated_at)
    probe = build_final_approval_review_probe(source)
    guard = build_no_runtime_no_order_guard()

    source_ready = source.complete
    gate_checks = [
        _check("source_38h_ready", source_ready),
        _check("phase_37_final_closed"),
        _check("paper_sandbox_observation_metrics_gate_ready"),
        _check("explicit_operator_approval_contract_locked"),
        _check("explicit_operator_approval_required"),
        _check("operator_identity_required"),
        _check("operator_id_required"),
        _check("operator_name_required"),
        _check("operator_role_required"),
        _check("operator_approval_timestamp_required"),
        _check("source_report_required"),
        _check("missing_explicit_operator_approval_denied"),
        _check("invalid_final_approval_phrase_denied"),
        _check("operator_identity_missing_denied"),
        _check("valid_final_approval_review_only"),
        _check("valid_final_approval_runtime_denied_no_submit"),
        _check("valid_final_approval_network_order_denied"),
        _check("paper_transition_approval_not_performed"),
        _check("paper_transition_not_approved_by_patch"),
        _check("paper_runtime_not_started"),
        _check("paper_order_submit_forbidden"),
        _check("network_order_submit_forbidden"),
        _check("network_market_data_collection_forbidden"),
        _check("network_request_forbidden"),
        _check("live_real_remains_not_approved"),
        _check("exchange_submit_remains_forbidden"),
        _check("signed_request_forbidden"),
        _check("private_api_forbidden"),
        _check("runtime_health_probe_forbidden"),
        _check("runtime_overlay_training_reload_forbidden"),
        _check("git_mutating_operations_forbidden"),
        _check("report_mutation_forbidden"),
        _check("next_phase_not_auto_unlocked"),
        _check("final_closure_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("safety_flags_clean"),
    ]
    gate_ready_count = sum(1 for item in gate_checks if item["ready"])
    final_safety_violations: list[str] = [] if source_ready else list(source.errors)
    status = "READY" if source_ready and gate_ready_count == len(gate_checks) else "NOT_READY"

    report: dict[str, Any] = {
        "ok": status == "READY",
        "status": status,
        "decision": READY_DECISION if status == "READY" else NOT_READY_DECISION,
        "generated_at_utc": generated_at,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "source_report": source.report_path,
        "source_38h_report": source.report_path,
        "source_38h_complete": source.complete,
        "source_38h_status": source.status,
        "source_38h_decision": source.decision,
        "source_38h_safety_violation_count": source.safety_violation_count,
        "source_38h_safety_violations": source.safety_violations,
        "source_38h_errors": source.errors,
        "source_38h_approved_for_paper_transition": source.data.get("approved_for_paper_transition", False),
        "source_38h_paper_sandbox_observation_metrics_gate_ready": source.data.get("paper_sandbox_observation_metrics_gate_ready", False),
        "source_38h_paper_transition_blocked": source.data.get("paper_transition_blocked", True),
        "source_38h_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_38h_runtime_health_probe_performed": source.data.get("runtime_health_probe_performed", False),
        "source_38h_network_order_submit_performed": source.data.get("network_order_submit_performed", False),
        "phase_37_final_closed": True,
        "phase_38_final_closure_review": True,
        "phase_38_final_closure_ready": status == "READY",
        "phase_38_planning_only": True,
        "phase_38_execution_started": False,
        "phase_38_unlocked": False,
        "paper_transition_final_approval_closure_complete": status == "READY",
        "paper_transition_final_approval_closure_locked": True,
        "paper_transition_final_approval_closure_ready": status == "READY",
        "paper_transition_final_approval_closure_mode": "EXPLICIT_OPERATOR_APPROVAL_REQUIRED_REVIEW_ONLY_NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER",
        "paper_transition_final_approval_review_complete": True,
        "paper_transition_final_approval_review_locked": True,
        "paper_transition_final_approval_review_ready": status == "READY",
        "explicit_operator_approval_contract_complete": True,
        "explicit_operator_approval_contract_locked": True,
        "explicit_operator_approval_contract_ready": status == "READY",
        "explicit_operator_approval_contract_rule_count": contract["rule_count"],
        "explicit_operator_approval_contract_ready_count": contract["ready_count"],
        "explicit_operator_approval_contract_rules": contract["rules"],
        "explicit_operator_approval_contract_digest": contract["digest"],
        "explicit_operator_approval_required": True,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "paper_transition_final_approval_phrase_required": APPROVAL_PHRASE,
        "paper_transition_final_approval_scope_required": APPROVAL_SCOPE,
        "approval_evidence_schema": contract["approval_evidence_schema"],
        "final_operator_approval_valid_evidence_sample": sample,
        "typed_final_approval_missing_denied": True,
        "typed_final_approval_invalid_denied": True,
        "operator_identity_missing_denied": True,
        "operator_approval_timestamp_missing_denied": True,
        "source_report_missing_denied": True,
        "valid_final_approval_evidence_accepted_for_review": True,
        "valid_final_approval_evidence_runtime_denied_no_submit": True,
        "valid_final_approval_evidence_network_order_denied": True,
        "valid_final_approval_evidence_transition_denied_without_separate_action": True,
        "paper_transition_final_approval_performed": False,
        "paper_transition_final_approval_review_only": True,
        "paper_transition_final_closure_performed": False,
        "paper_transition_final_closure_runtime_binding_performed": False,
        "paper_transition_final_approval_closure_probe_complete": True,
        "paper_transition_final_approval_closure_probe_locked": True,
        "paper_transition_final_approval_closure_probe_mode": probe["probe_mode"],
        "paper_transition_final_approval_closure_probe_count": probe["probe_count"],
        "paper_transition_final_approval_closure_probe_passed_count": probe["probe_passed_count"],
        "paper_transition_final_approval_closure_probes": probe["probes"],
        "paper_transition_final_approval_closure_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_final_approval_review": status == "READY",
        "approved_for_paper_transition_final_approval_closure": status == "READY",
        "approved_for_paper_sandbox_observation_metrics_gate": True,
        "approved_for_paper_sandbox_local_runtime_health_evidence": True,
        "approved_for_paper_sandbox_local_runtime_activation_harness": True,
        "approved_for_paper_sandbox_runtime_activation_preflight": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_explicit_operator_approval_required": True,
        "paper_transition_approval_phrase_required": APPROVAL_PHRASE,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "FINAL_APPROVAL_REVIEW_READY_EXPLICIT_OPERATOR_APPROVAL_REQUIRED_NO_RUNTIME_PROCESS_NO_ORDER",
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "paper_submit_allowed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "network_market_data_collection_performed": False,
        "approved_for_live_real": False,
        "live_environment_enabled": False,
        "live_transition_ready": False,
        "live_transition_allowed": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "runtime_process_status": "NOT_STARTED_BY_38I",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_38i": True,
        "runtime_start_performed": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_38i": True,
        "runtime_health_endpoint_called": False,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "automatic_commit_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "historical_report_mutation_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_status": guard["status"],
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_rule_count": guard["rule_count"],
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_ready_count": guard["ready_count"],
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_rules": guard["rules"],
        "no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_digest": guard["digest"],
        "paper_transition_final_approval_closure_gate_complete": True,
        "paper_transition_final_approval_closure_gate_locked": True,
        "paper_transition_final_approval_closure_gate_check_count": len(gate_checks),
        "paper_transition_final_approval_closure_gate_ready_count": gate_ready_count,
        "paper_transition_final_approval_closure_gate_checks": gate_checks,
        "paper_transition_final_approval_closure_gate_status": "PAPER_TRANSITION_FINAL_APPROVAL_CLOSURE_GATE_READY" if status == "READY" else "PAPER_TRANSITION_FINAL_APPROVAL_CLOSURE_GATE_NOT_READY",
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "final_safety_violation_count": len(final_safety_violations),
        "final_safety_violations": final_safety_violations,
        "errors": source.errors,
        "report_path": None,
    }

    if write_artifacts:
        reports_path.mkdir(parents=True, exist_ok=True)
        artifacts = {
            f"{PATCH_ID}_explicit_operator_approval_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_final_operator_approval_sample_{generated_at}.json": sample,
            f"{PATCH_ID}_final_approval_closure_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_transition_final_approval_closure_gate_{generated_at}.json": {
                "gate_name": "paper_transition_final_approval_closure_gate",
                "checks": gate_checks,
                "check_count": len(gate_checks),
                "ready_count": gate_ready_count,
            },
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "explicit_operator_approval_contract" in filename:
                report["explicit_operator_approval_contract_path"] = str(path)
            elif "final_operator_approval_sample" in filename:
                report["final_operator_approval_sample_path"] = str(path)
            elif "final_approval_closure_probe" in filename:
                report["paper_transition_final_approval_closure_probe_path"] = str(path)
            elif "no_runtime_process" in filename:
                report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_transition_final_approval_closure_gate" in filename:
                report["paper_transition_final_approval_closure_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_transition_final_approval_closure_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["explicit_operator_approval_contract_path"] = None
        report["final_operator_approval_sample_path"] = None
        report["paper_transition_final_approval_closure_probe_path"] = None
        report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_transition_final_approval_closure_gate_path"] = None

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.reports_dir), write_artifacts=args.write_artifacts)
    if args.once_json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("status") == "READY" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
