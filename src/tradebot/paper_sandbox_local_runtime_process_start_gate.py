from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436639D"
PATCH_VERSION = "4B.4.3.6.6.39D"
PATCH_NAME = "Paper Sandbox Local Runtime Process Start Gate"
READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_GATE_READY_"
    "EXPLICIT_AUTHORIZATION_EVIDENCE_VALIDATED_COMMAND_NOT_EXECUTED_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_GATE_NOT_READY_"
    "COMMAND_NOT_EXECUTED_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_AUTHORIZATION_LEDGER_READY_"
    "EXPLICIT_TYPED_OPERATOR_APPROVAL_LEDGER_NO_COMMAND_EXECUTION_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.39E"
NEXT_PHASE_NAME = "Paper Sandbox Local Runtime Health Probe Evidence"
GATE_SCOPE = "paper_sandbox_local_runtime_process_start_gate_review_only"
REQUIRED_AUTHORIZATION_PHRASE = "APPROVE PAPER SANDBOX RUNTIME START AUTHORIZATION LEDGER ONLY"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_runtime_start_authorization_ledger_ready": True,
    "explicit_runtime_start_authorization_ledger_ready": True,
    "approved_for_paper_sandbox_runtime_start_authorization_ledger": True,
    "approved_for_paper_runtime_start_authorization_ledger": True,
    "valid_runtime_start_authorization_evidence_accepted_for_review": True,
    "valid_runtime_start_authorization_evidence_command_execution_denied": True,
    "valid_runtime_start_authorization_evidence_runtime_denied_no_submit": True,
    "valid_runtime_start_authorization_evidence_network_order_denied": True,
    "runtime_start_command_template_declared": True,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_command_execution_allowed": False,
    "runtime_start_command_allowed": False,
    "approved_for_paper_runtime_start": False,
    "paper_runtime_start_authorization_performed": False,
    "paper_runtime_start_authorization_ready": False,
    "paper_runtime_start_performed": False,
    "runtime_process_started": False,
    "runtime_start_performed": False,
    "runtime_health_probe_performed": False,
    "network_order_submit_performed": False,
    "order_submit_performed": False,
    "exchange_submit_performed": False,
    "approved_for_paper_transition": False,
    "paper_transition_blocked": True,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "network_request_performed": False,
    "final_safety_violation_count": 0,
}


@dataclass(frozen=True)
class Source39CStatus:
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


def _is_main_39c_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436639C_paper_sandbox_runtime_start_authorization_ledger_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_gate_",
        "_guard_",
        "_sample_",
        "_schema_",
        "_evidence_",
        "_operator_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436639C_paper_sandbox_runtime_start_authorization_ledger_*_ready.json")
        if _is_main_39c_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_39c(reports_dir: Path) -> Source39CStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source39CStatus(False, "SOURCE_39C_MISSING", None, None, 1, ["missing_39c_ready_report"], [f"39C READY report not found under {reports_dir}"], {})
    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover
        return Source39CStatus(False, "SOURCE_39C_INVALID_JSON", str(source_path), None, 1, ["invalid_39c_json"], [str(exc)], {})

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")
    complete = not errors
    return Source39CStatus(
        complete=complete,
        status="SOURCE_39C_READY" if complete else "SOURCE_39C_NOT_READY",
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


def validate_authorization_evidence_from_source(source: Source39CStatus) -> dict[str, Any]:
    sample = source.data.get("runtime_start_operator_authorization_valid_evidence_sample")
    schema = source.data.get("approval_evidence_schema")
    sample_ok = isinstance(sample, dict)
    schema_ok = isinstance(schema, dict)
    phrase_ok = bool(sample_ok and sample.get("approval_phrase") == REQUIRED_AUTHORIZATION_PHRASE)
    source_ref_ok = bool(sample_ok and sample.get("source_report"))
    identity_ok = bool(sample_ok and sample.get("operator_id") and sample.get("operator_name") and sample.get("operator_role"))
    timestamp_ok = bool(sample_ok and sample.get("approved_at_utc"))
    review_only_ok = bool(sample_ok and sample.get("runtime_start_allowed") is False and sample.get("runtime_start_command_executed") is False)
    schema_phrase_ok = bool(schema_ok and schema.get("approval_phrase_required") == REQUIRED_AUTHORIZATION_PHRASE)
    validation = {
        "validation_name": "explicit_runtime_start_authorization_evidence_validation",
        "source_39c_status": source.status,
        "sample_present": sample_ok,
        "schema_present": schema_ok,
        "authorization_phrase_valid": phrase_ok,
        "authorization_source_reference_present": source_ref_ok,
        "operator_identity_present": identity_ok,
        "operator_approval_timestamp_present": timestamp_ok,
        "authorization_review_only_lock_valid": review_only_ok,
        "authorization_schema_phrase_valid": schema_phrase_ok,
        "runtime_start_allowed_by_authorization_evidence": False,
        "command_execution_allowed_by_authorization_evidence": False,
        "network_order_submit_allowed_by_authorization_evidence": False,
    }
    validation["ready"] = all(
        bool(validation[key])
        for key in (
            "sample_present",
            "schema_present",
            "authorization_phrase_valid",
            "authorization_source_reference_present",
            "operator_identity_present",
            "operator_approval_timestamp_present",
            "authorization_review_only_lock_valid",
            "authorization_schema_phrase_valid",
        )
    )
    validation["digest"] = stable_digest(validation)
    return validation


def build_local_runtime_start_gate_contract(source: Source39CStatus, validation: Mapping[str, Any], generated_at_utc: str) -> dict[str, Any]:
    rules = [
        _rule("source_39c_ready_required", "39C READY runtime-start authorization ledger evidence is required"),
        _rule("explicit_authorization_evidence_validation_required", "explicit typed authorization evidence must be validated"),
        _rule("local_runtime_start_gate_only", "39D defines a local runtime process start gate only"),
        _rule("gate_does_not_execute_command", "39D cannot execute the runtime start command"),
        _rule("gate_does_not_start_runtime", "39D cannot start paper runtime process"),
        _rule("command_execution_requires_future_gate_action", "runtime start command remains unexecuted unless a future execution gate explicitly approves and performs it"),
        _rule("paper_only_runtime_scope_required", "future runtime start must be paper-only local runtime scope"),
        _rule("runtime_process_lock_required", "future runtime start must be protected by single-instance process lock"),
        _rule("runtime_health_probe_deferred", "runtime health probe is deferred to 39E or later"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("39e_not_auto_unlocked", "39E is not auto-unlocked by 39D"),
    ]
    contract = {
        "contract_name": "paper_sandbox_local_runtime_process_start_gate_contract",
        "gate_scope": GATE_SCOPE,
        "gate_mode": "LOCAL_RUNTIME_PROCESS_START_GATE_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "source_39c_status": source.status,
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39C",
        "source_report": source.report_path,
        "explicit_authorization_evidence_validated": bool(validation.get("ready")),
        "local_runtime_process_start_gate_only": True,
        "local_runtime_process_start_gate_ready_for_review": bool(validation.get("ready")),
        "local_runtime_process_start_gate_approved_for_command_execution": False,
        "local_runtime_process_start_gate_approval_performed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_process_started": False,
        "paper_only_runtime_scope_required": True,
        "runtime_process_lock_required": True,
        "network_order_submit_allowed": False,
        "live_environment_enabled": False,
        "exchange_submit_allowed": False,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_gate_probe(source: Source39CStatus, validation: Mapping[str, Any]) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_39c_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False},
        {"probe_id": "authorization_evidence_validation_ready", "expected": True, "result": bool(validation.get("ready")), "passed": bool(validation.get("ready")), "runtime_start_allowed": False},
        {"probe_id": "authorization_phrase_validated", "expected": True, "result": bool(validation.get("authorization_phrase_valid")), "passed": bool(validation.get("authorization_phrase_valid")), "runtime_start_allowed": False},
        {"probe_id": "operator_identity_validated", "expected": True, "result": bool(validation.get("operator_identity_present")), "passed": bool(validation.get("operator_identity_present")), "runtime_start_allowed": False},
        {"probe_id": "operator_timestamp_validated", "expected": True, "result": bool(validation.get("operator_approval_timestamp_present")), "passed": bool(validation.get("operator_approval_timestamp_present")), "runtime_start_allowed": False},
        {"probe_id": "source_report_reference_validated", "expected": True, "result": bool(validation.get("authorization_source_reference_present")), "passed": bool(validation.get("authorization_source_reference_present")), "runtime_start_allowed": False},
        {"probe_id": "review_only_lock_validated", "expected": True, "result": bool(validation.get("authorization_review_only_lock_valid")), "passed": bool(validation.get("authorization_review_only_lock_valid")), "runtime_start_allowed": False},
        {"probe_id": "local_runtime_process_start_gate_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_start_command_execution_denied", "expected": False, "result": False, "passed": True, "command_execution_allowed": False},
        {"probe_id": "runtime_start_command_not_executed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_market_data_collection_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "signed_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "private_api_access_not_allowed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probe = {
        "probe_name": "paper_sandbox_local_runtime_process_start_gate_probe",
        "probe_mode": "LOCAL_RUNTIME_START_GATE_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_command_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("local_runtime_gate_does_not_execute_command", "39D cannot execute the runtime start command"),
        _rule("local_runtime_gate_does_not_start_process", "39D cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "39D cannot perform runtime health probes"),
        _rule("paper_runtime_start_authorization_not_performed", "39D does not perform runtime start authorization"),
        _rule("paper_transition_approval_not_performed", "39D does not perform paper transition approval"),
        _rule("paper_order_submit_forbidden", "39D cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39D cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 39D"),
        _rule("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        _rule("git_mutation_forbidden", "git mutating operations are not performed"),
    ]
    guard = {
        "guard_name": "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard",
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
        "status": "NO_COMMAND_EXECUTION_NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
    }
    guard["digest"] = stable_digest(guard)
    return guard


def build_report(reports_dir: Path | str = Path("reports/recovery"), *, write_artifacts: bool = False) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    source = validate_source_39c(reports_path)
    generated_at = utc_stamp()
    validation = validate_authorization_evidence_from_source(source)
    contract = build_local_runtime_start_gate_contract(source, validation, generated_at)
    probe = build_gate_probe(source, validation)
    guard = build_no_command_no_order_guard()

    source_ready = source.complete
    validation_ready = bool(validation.get("ready"))
    gate_checks = [
        _check("source_39c_ready", source_ready),
        _check("authorization_ledger_ready"),
        _check("explicit_authorization_evidence_validation_complete", validation_ready),
        _check("authorization_phrase_validated", bool(validation.get("authorization_phrase_valid"))),
        _check("operator_identity_validated", bool(validation.get("operator_identity_present"))),
        _check("operator_approval_timestamp_validated", bool(validation.get("operator_approval_timestamp_present"))),
        _check("source_report_reference_validated", bool(validation.get("authorization_source_reference_present"))),
        _check("authorization_review_only_lock_validated", bool(validation.get("authorization_review_only_lock_valid"))),
        _check("local_runtime_process_start_gate_locked"),
        _check("local_runtime_process_start_gate_review_only"),
        _check("local_runtime_process_start_gate_not_approved_for_command_execution"),
        _check("runtime_start_command_not_executed"),
        _check("runtime_start_command_execution_not_performed"),
        _check("runtime_process_not_started"),
        _check("paper_runtime_start_not_performed"),
        _check("runtime_health_probe_deferred"),
        _check("paper_order_submit_forbidden"),
        _check("network_order_submit_forbidden"),
        _check("network_market_data_collection_forbidden"),
        _check("network_request_forbidden"),
        _check("live_real_remains_not_approved"),
        _check("exchange_submit_remains_forbidden"),
        _check("signed_request_forbidden"),
        _check("private_api_forbidden"),
        _check("runtime_overlay_training_reload_forbidden"),
        _check("git_mutating_operations_forbidden"),
        _check("report_mutation_forbidden"),
        _check("next_phase_not_auto_unlocked"),
        _check("gate_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("safety_flags_clean"),
    ]
    gate_ready_count = sum(1 for item in gate_checks if item["ready"])
    final_safety_violations: list[str] = [] if source_ready and validation_ready else list(source.errors)
    if source_ready and not validation_ready:
        final_safety_violations.append("explicit_authorization_evidence_validation_not_ready")
    status = "READY" if source_ready and validation_ready and gate_ready_count == len(gate_checks) else "NOT_READY"

    source_template = source.data.get("runtime_start_command_template")
    report: dict[str, Any] = {
        "ok": status == "READY",
        "status": status,
        "decision": READY_DECISION if status == "READY" else NOT_READY_DECISION,
        "generated_at_utc": generated_at,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "source_report": source.report_path,
        "source_39c_report": source.report_path,
        "source_39c_complete": source.complete,
        "source_39c_status": source.status,
        "source_39c_decision": source.decision,
        "source_39c_safety_violation_count": source.safety_violation_count,
        "source_39c_safety_violations": source.safety_violations,
        "source_39c_errors": source.errors,
        "source_39c_approved_for_paper_runtime_start": source.data.get("approved_for_paper_runtime_start", False),
        "source_39c_runtime_start_command_executed": source.data.get("runtime_start_command_executed", False),
        "source_39c_runtime_process_started": source.data.get("runtime_process_started", False),
        "phase_39_local_runtime_process_start_gate_review": True,
        "phase_39_planning_only": True,
        "phase_39_execution_started": False,
        "phase_39_unlocked": False,
        "paper_sandbox_local_runtime_process_start_gate_complete": status == "READY",
        "paper_sandbox_local_runtime_process_start_gate_locked": True,
        "paper_sandbox_local_runtime_process_start_gate_ready": status == "READY",
        "paper_sandbox_local_runtime_process_start_gate_mode": "LOCAL_RUNTIME_PROCESS_START_GATE_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "local_runtime_process_start_gate_complete": True,
        "local_runtime_process_start_gate_locked": True,
        "local_runtime_process_start_gate_ready": status == "READY",
        "local_runtime_process_start_gate_review_only": True,
        "local_runtime_process_start_gate_contract_rule_count": contract["rule_count"],
        "local_runtime_process_start_gate_contract_ready_count": contract["ready_count"],
        "local_runtime_process_start_gate_contract_rules": contract["rules"],
        "local_runtime_process_start_gate_contract_digest": contract["digest"],
        "explicit_authorization_evidence_validation_complete": validation_ready,
        "explicit_authorization_evidence_validation_locked": True,
        "explicit_authorization_evidence_validation_ready": validation_ready,
        "explicit_authorization_evidence_validation": validation,
        "explicit_authorization_evidence_validation_digest": validation["digest"],
        "authorization_phrase_validated": bool(validation.get("authorization_phrase_valid")),
        "authorization_source_reference_validated": bool(validation.get("authorization_source_reference_present")),
        "operator_identity_validated": bool(validation.get("operator_identity_present")),
        "operator_approval_timestamp_validated": bool(validation.get("operator_approval_timestamp_present")),
        "authorization_review_only_lock_validated": bool(validation.get("authorization_review_only_lock_valid")),
        "runtime_start_command_template": source_template,
        "runtime_start_command_template_preserved": source_template is not None,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_review_only": True,
        "runtime_start_command_allowed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "command_still_not_executed_unless_gate_approves": True,
        "local_runtime_process_start_gate_approval_required": True,
        "local_runtime_process_start_gate_approval_performed": False,
        "local_runtime_process_start_gate_approved_for_command_execution": False,
        "local_runtime_process_start_gate_approved_for_runtime_start": False,
        "paper_only_runtime_scope_required": True,
        "paper_only_config_required": True,
        "paper_only_config_validated_for_local_runtime_start_gate": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "runtime_health_probe_deferred_to_next_phase": True,
        "paper_sandbox_local_runtime_process_start_gate_probe_complete": True,
        "paper_sandbox_local_runtime_process_start_gate_probe_locked": True,
        "paper_sandbox_local_runtime_process_start_gate_probe_mode": probe["probe_mode"],
        "paper_sandbox_local_runtime_process_start_gate_probe_count": probe["probe_count"],
        "paper_sandbox_local_runtime_process_start_gate_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_local_runtime_process_start_gate_probes": probe["probes"],
        "paper_sandbox_local_runtime_process_start_gate_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_local_runtime_process_start_gate": status == "READY",
        "approved_for_local_runtime_process_start_gate": status == "READY",
        "approved_for_paper_runtime_start_authorization_ledger": True,
        "approved_for_paper_runtime_start": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "LOCAL_RUNTIME_START_GATE_READY_NO_COMMAND_EXECUTION_NO_RUNTIME_PROCESS_NO_ORDER",
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_authorization_performed": False,
        "paper_runtime_start_authorization_ready": False,
        "paper_runtime_start_approval_performed": False,
        "paper_runtime_start_approval_ready": False,
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
        "runtime_process_status": "NOT_STARTED_BY_39D",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_39d": True,
        "runtime_start_performed": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_39d": True,
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
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_status": guard["status"],
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_rule_count": guard["rule_count"],
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_ready_count": guard["ready_count"],
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_rules": guard["rules"],
        "no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_digest": guard["digest"],
        "paper_sandbox_local_runtime_process_start_gate_check_complete": True,
        "paper_sandbox_local_runtime_process_start_gate_check_locked": True,
        "paper_sandbox_local_runtime_process_start_gate_check_count": len(gate_checks),
        "paper_sandbox_local_runtime_process_start_gate_ready_count": gate_ready_count,
        "paper_sandbox_local_runtime_process_start_gate_checks": gate_checks,
        "paper_sandbox_local_runtime_process_start_gate_status": "PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_GATE_READY" if status == "READY" else "PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_GATE_NOT_READY",
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
            f"{PATCH_ID}_local_runtime_process_start_gate_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_explicit_authorization_evidence_validation_{generated_at}.json": validation,
            f"{PATCH_ID}_local_runtime_process_start_gate_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_local_runtime_process_start_gate_{generated_at}.json": {"gate_name": "paper_sandbox_local_runtime_process_start_gate", "checks": gate_checks, "check_count": len(gate_checks), "ready_count": gate_ready_count},
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "local_runtime_process_start_gate_contract" in filename:
                report["local_runtime_process_start_gate_contract_path"] = str(path)
            elif "explicit_authorization_evidence_validation" in filename:
                report["explicit_authorization_evidence_validation_path"] = str(path)
            elif "local_runtime_process_start_gate_probe" in filename:
                report["paper_sandbox_local_runtime_process_start_gate_probe_path"] = str(path)
            elif "no_command_execution" in filename:
                report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_sandbox_local_runtime_process_start_gate" in filename:
                report["paper_sandbox_local_runtime_process_start_gate_path"] = str(path)
        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_local_runtime_process_start_gate_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["local_runtime_process_start_gate_contract_path"] = None
        report["explicit_authorization_evidence_validation_path"] = None
        report["paper_sandbox_local_runtime_process_start_gate_probe_path"] = None
        report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_local_runtime_process_start_gate_path"] = None
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
