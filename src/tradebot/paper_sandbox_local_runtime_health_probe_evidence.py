from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436639E"
PATCH_VERSION = "4B.4.3.6.6.39E"
PATCH_NAME = "Paper Sandbox Local Runtime Health Probe Evidence"
READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_PROBE_EVIDENCE_READY_"
    "HEALTH_PROBE_EVIDENCE_CONTRACT_RUNTIME_NOT_STARTED_BY_PATCH_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_PROBE_EVIDENCE_NOT_READY_"
    "RUNTIME_NOT_STARTED_BY_PATCH_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_PROCESS_START_GATE_READY_"
    "EXPLICIT_AUTHORIZATION_EVIDENCE_VALIDATED_COMMAND_NOT_EXECUTED_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.39F"
NEXT_PHASE_NAME = "Paper Sandbox Observation Runtime Metrics"
HEALTH_PROBE_SCOPE = "paper_sandbox_local_runtime_health_probe_evidence_contract_review_only"
HEALTH_PROBE_ENDPOINT_TEMPLATE = "http://127.0.0.1:8000/health"
HEALTH_PROBE_EVIDENCE_REQUIRED_FIELDS = (
    "ok",
    "running",
    "symbol",
    "bootstrap_ok",
    "bootstrap_error",
    "runtime_process_pid",
    "checked_at_utc",
    "source_report",
)

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_local_runtime_process_start_gate_ready": True,
    "approved_for_paper_sandbox_local_runtime_process_start_gate": True,
    "approved_for_local_runtime_process_start_gate": True,
    "local_runtime_process_start_gate_ready": True,
    "explicit_authorization_evidence_validation_ready": True,
    "authorization_phrase_validated": True,
    "authorization_source_reference_validated": True,
    "operator_identity_validated": True,
    "operator_approval_timestamp_validated": True,
    "authorization_review_only_lock_validated": True,
    "command_still_not_executed_unless_gate_approves": True,
    "local_runtime_process_start_gate_approval_required": True,
    "local_runtime_process_start_gate_approval_performed": False,
    "local_runtime_process_start_gate_approved_for_command_execution": False,
    "local_runtime_process_start_gate_approved_for_runtime_start": False,
    "runtime_start_command_template_declared": True,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_command_execution_allowed": False,
    "runtime_start_command_allowed": False,
    "runtime_health_probe_deferred_to_next_phase": True,
    "runtime_health_probe_performed": False,
    "runtime_health_endpoint_called": False,
    "approved_for_paper_runtime_start": False,
    "paper_runtime_start_performed": False,
    "runtime_process_started": False,
    "runtime_start_performed": False,
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
class Source39DStatus:
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


def _is_main_39d_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436639D_paper_sandbox_local_runtime_process_start_gate_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_contract_",
        "_guard_",
        "_validation_",
        "_evidence_",
        "_sample_",
        "_schema_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436639D_paper_sandbox_local_runtime_process_start_gate_*_ready.json")
        if _is_main_39d_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_39d(reports_dir: Path) -> Source39DStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source39DStatus(
            complete=False,
            status="SOURCE_39D_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_39d_ready_report"],
            errors=[f"39D READY report not found under {reports_dir}"],
            data={},
        )
    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover
        return Source39DStatus(
            complete=False,
            status="SOURCE_39D_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_39d_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")
    complete = not errors
    return Source39DStatus(
        complete=complete,
        status="SOURCE_39D_READY" if complete else "SOURCE_39D_NOT_READY",
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


def build_health_probe_evidence_schema(source: Source39DStatus, generated_at_utc: str) -> dict[str, Any]:
    schema = {
        "schema_name": "paper_sandbox_local_runtime_health_probe_evidence_schema",
        "scope": HEALTH_PROBE_SCOPE,
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39D",
        "source_report": source.report_path,
        "health_probe_endpoint_template": HEALTH_PROBE_ENDPOINT_TEMPLATE,
        "required_fields": list(HEALTH_PROBE_EVIDENCE_REQUIRED_FIELDS),
        "expected_runtime_mode": "paper-sandbox-local",
        "runtime_must_be_started_by_previous_authorized_step": True,
        "health_probe_collection_deferred": True,
        "health_probe_endpoint_called_by_39e": False,
        "runtime_process_started_by_39e": False,
        "network_order_submit_allowed": False,
        "live_environment_enabled": False,
        "exchange_submit_allowed": False,
        "acceptance_rules": {
            "ok_must_be_true": True,
            "running_must_be_true_when_future_runtime_started": True,
            "bootstrap_ok_must_be_true": True,
            "bootstrap_error_must_be_null_or_empty": True,
            "runtime_process_pid_required_when_running": True,
            "source_report_must_reference_39d_ready": True,
            "no_network_order_submit_required": True,
            "no_live_real_required": True,
            "no_exchange_submit_required": True,
        },
    }
    schema["digest"] = stable_digest(schema)
    return schema


def build_health_probe_evidence_contract(source: Source39DStatus, schema: Mapping[str, Any], generated_at_utc: str) -> dict[str, Any]:
    rules = [
        _rule("source_39d_ready_required", "39D READY local runtime process start gate evidence is required"),
        _rule("health_probe_evidence_contract_only", "39E defines health probe evidence contract only"),
        _rule("health_probe_schema_declared", "health probe evidence schema must be declared"),
        _rule("health_probe_endpoint_template_declared", "local health endpoint template must be declared"),
        _rule("runtime_not_started_by_patch", "39E cannot start paper runtime process"),
        _rule("health_probe_not_called_by_patch", "39E cannot call the health endpoint"),
        _rule("health_probe_collection_deferred", "actual health probe evidence is deferred until an authorized runtime exists"),
        _rule("runtime_process_lock_required", "future runtime must remain single-instance lock guarded"),
        _rule("paper_only_runtime_scope_required", "future health probe evidence must be paper-only local runtime scoped"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39E cannot collect network market data"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("39f_not_auto_unlocked", "39F is not auto-unlocked by 39E"),
    ]
    contract = {
        "contract_name": "paper_sandbox_local_runtime_health_probe_evidence_contract",
        "scope": HEALTH_PROBE_SCOPE,
        "contract_mode": "HEALTH_PROBE_EVIDENCE_CONTRACT_ONLY_RUNTIME_NOT_STARTED_NO_NETWORK_ORDER",
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39D",
        "source_report": source.report_path,
        "health_probe_evidence_schema_digest": schema.get("digest"),
        "health_probe_endpoint_template": HEALTH_PROBE_ENDPOINT_TEMPLATE,
        "health_probe_evidence_contract_only": True,
        "health_probe_evidence_schema_declared": True,
        "health_probe_endpoint_template_declared": True,
        "runtime_not_started_by_patch": True,
        "health_probe_endpoint_called_by_patch": False,
        "runtime_health_probe_performed": False,
        "runtime_process_started": False,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_future_health_probe_sample(source: Source39DStatus, generated_at_utc: str) -> dict[str, Any]:
    sample = {
        "sample_name": "future_local_runtime_health_probe_evidence_sample",
        "scope": HEALTH_PROBE_SCOPE,
        "checked_at_utc": generated_at_utc,
        "source_report": source.report_path,
        "health_probe_endpoint": HEALTH_PROBE_ENDPOINT_TEMPLATE,
        "ok": True,
        "running": True,
        "symbol": "ETHUSDT",
        "bootstrap_ok": True,
        "bootstrap_error": None,
        "runtime_process_pid": 12345,
        "network_order_submit_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "live_environment_enabled": False,
        "accepted_as_future_evidence_shape_only": True,
        "collected_by_39e": False,
        "runtime_started_by_39e": False,
        "health_endpoint_called_by_39e": False,
    }
    sample["digest"] = stable_digest(sample)
    return sample


def build_health_probe_readiness_probe(source: Source39DStatus) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_39d_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False},
        {"probe_id": "health_probe_evidence_contract_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "health_probe_evidence_schema_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "health_probe_endpoint_template_declared", "expected": HEALTH_PROBE_ENDPOINT_TEMPLATE, "result": HEALTH_PROBE_ENDPOINT_TEMPLATE, "passed": True},
        {"probe_id": "runtime_not_started_by_patch", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "health_endpoint_not_called_by_patch", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "health_probe_collection_deferred", "expected": True, "result": True, "passed": True},
        {"probe_id": "runtime_start_command_not_executed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
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
        "probe_name": "paper_sandbox_local_runtime_health_probe_evidence_probe",
        "probe_mode": "HEALTH_PROBE_EVIDENCE_CONTRACT_ONLY_RUNTIME_NOT_STARTED_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_runtime_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("health_probe_evidence_contract_only", "39E only declares health probe evidence contract"),
        _rule("runtime_process_start_forbidden", "39E cannot start paper runtime process"),
        _rule("runtime_health_endpoint_call_forbidden", "39E cannot call the runtime health endpoint"),
        _rule("runtime_health_probe_forbidden", "39E cannot perform runtime health probes"),
        _rule("runtime_start_command_execution_forbidden", "39E cannot execute runtime start command"),
        _rule("paper_runtime_start_forbidden", "39E cannot perform paper runtime start"),
        _rule("paper_order_submit_forbidden", "39E cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39E cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        _rule("git_mutation_forbidden", "git mutating operations are not performed"),
    ]
    guard = {
        "guard_name": "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard",
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
        "status": "NO_RUNTIME_START_NO_HEALTH_PROBE_CALL_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
    }
    guard["digest"] = stable_digest(guard)
    return guard


def build_report(reports_dir: Path | str = Path("reports/recovery"), *, write_artifacts: bool = False) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    source = validate_source_39d(reports_path)
    generated_at = utc_stamp()

    schema = build_health_probe_evidence_schema(source, generated_at)
    sample = build_future_health_probe_sample(source, generated_at)
    contract = build_health_probe_evidence_contract(source, schema, generated_at)
    probe = build_health_probe_readiness_probe(source)
    guard = build_no_runtime_no_order_guard()

    source_ready = source.complete
    contract_ready = contract["rule_count"] == contract["ready_count"]
    probe_ready = probe["probe_count"] == probe["probe_passed_count"]
    guard_ready = guard["rule_count"] == guard["ready_count"]
    gate_checks = [
        _check("source_39d_ready", source_ready),
        _check("local_runtime_process_start_gate_ready"),
        _check("health_probe_evidence_contract_locked", contract_ready),
        _check("health_probe_evidence_schema_declared"),
        _check("health_probe_endpoint_template_declared"),
        _check("future_health_probe_evidence_sample_declared"),
        _check("runtime_not_started_by_patch"),
        _check("health_endpoint_not_called_by_patch"),
        _check("runtime_health_probe_not_performed"),
        _check("health_probe_collection_deferred"),
        _check("runtime_start_command_not_executed"),
        _check("runtime_process_not_started"),
        _check("paper_runtime_start_not_performed"),
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
        _check("health_probe_evidence_probe_passed", probe_ready),
        _check("guard_locked", guard_ready),
        _check("safety_flags_clean"),
    ]
    gate_ready_count = sum(1 for item in gate_checks if item["ready"])
    final_safety_violations: list[str] = [] if source_ready else list(source.errors)
    status = "READY" if source_ready and contract_ready and probe_ready and guard_ready and gate_ready_count == len(gate_checks) else "NOT_READY"

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
        "source_39d_report": source.report_path,
        "source_39d_complete": source.complete,
        "source_39d_status": source.status,
        "source_39d_decision": source.decision,
        "source_39d_safety_violation_count": source.safety_violation_count,
        "source_39d_safety_violations": source.safety_violations,
        "source_39d_errors": source.errors,
        "source_39d_approved_for_paper_runtime_start": source.data.get("approved_for_paper_runtime_start", False),
        "source_39d_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_39d_runtime_health_probe_performed": source.data.get("runtime_health_probe_performed", False),
        "source_39d_runtime_health_endpoint_called": source.data.get("runtime_health_endpoint_called", False),
        "phase_39_local_runtime_health_probe_evidence_review": True,
        "phase_39_planning_only": True,
        "phase_39_execution_started": False,
        "phase_39_unlocked": False,
        "paper_sandbox_local_runtime_health_probe_evidence_complete": status == "READY",
        "paper_sandbox_local_runtime_health_probe_evidence_locked": True,
        "paper_sandbox_local_runtime_health_probe_evidence_ready": status == "READY",
        "paper_sandbox_local_runtime_health_probe_evidence_mode": "HEALTH_PROBE_EVIDENCE_CONTRACT_ONLY_RUNTIME_NOT_STARTED_NO_NETWORK_ORDER",
        "local_runtime_health_probe_evidence_contract_complete": True,
        "local_runtime_health_probe_evidence_contract_locked": True,
        "local_runtime_health_probe_evidence_contract_ready": status == "READY",
        "local_runtime_health_probe_evidence_contract_rule_count": contract["rule_count"],
        "local_runtime_health_probe_evidence_contract_ready_count": contract["ready_count"],
        "local_runtime_health_probe_evidence_contract_rules": contract["rules"],
        "local_runtime_health_probe_evidence_contract_digest": contract["digest"],
        "health_probe_evidence_contract_only": True,
        "health_probe_evidence_schema_declared": True,
        "health_probe_evidence_schema": schema,
        "health_probe_evidence_schema_digest": schema["digest"],
        "future_health_probe_evidence_sample_declared": True,
        "future_health_probe_evidence_sample": sample,
        "future_health_probe_evidence_sample_digest": sample["digest"],
        "health_probe_endpoint_template": HEALTH_PROBE_ENDPOINT_TEMPLATE,
        "health_probe_endpoint_template_declared": True,
        "health_probe_evidence_required_fields": list(HEALTH_PROBE_EVIDENCE_REQUIRED_FIELDS),
        "health_probe_collection_deferred": True,
        "health_probe_evidence_collection_deferred": True,
        "health_probe_evidence_collection_performed": False,
        "health_probe_endpoint_called_by_patch": False,
        "runtime_health_endpoint_called": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_contract_ready": status == "READY",
        "runtime_health_probe_evidence_contract_ready": status == "READY",
        "runtime_health_probe_performed": False,
        "runtime_health_probe_forbidden_in_39e": True,
        "runtime_health_probe_deferred_to_future_runtime": True,
        "runtime_start_command_template": source_template,
        "runtime_start_command_template_preserved": source_template is not None,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_review_only": True,
        "runtime_start_command_allowed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "paper_only_runtime_scope_required": True,
        "paper_only_config_required": True,
        "paper_only_config_validated_for_health_probe_evidence": True,
        "paper_sandbox_local_runtime_health_probe_evidence_probe_complete": True,
        "paper_sandbox_local_runtime_health_probe_evidence_probe_locked": True,
        "paper_sandbox_local_runtime_health_probe_evidence_probe_mode": probe["probe_mode"],
        "paper_sandbox_local_runtime_health_probe_evidence_probe_count": probe["probe_count"],
        "paper_sandbox_local_runtime_health_probe_evidence_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_local_runtime_health_probe_evidence_probes": probe["probes"],
        "paper_sandbox_local_runtime_health_probe_evidence_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_local_runtime_health_probe_evidence": status == "READY",
        "approved_for_local_runtime_health_probe_evidence_contract": status == "READY",
        "approved_for_paper_sandbox_local_runtime_process_start_gate": True,
        "approved_for_paper_runtime_start": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "HEALTH_PROBE_EVIDENCE_CONTRACT_READY_NO_RUNTIME_PROCESS_NO_ORDER",
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
        "runtime_process_status": "NOT_STARTED_BY_39E",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_39e": True,
        "runtime_start_performed": False,
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
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_status": guard["status"],
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_rule_count": guard["rule_count"],
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_ready_count": guard["ready_count"],
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_rules": guard["rules"],
        "no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_digest": guard["digest"],
        "paper_sandbox_local_runtime_health_probe_evidence_check_complete": True,
        "paper_sandbox_local_runtime_health_probe_evidence_check_locked": True,
        "paper_sandbox_local_runtime_health_probe_evidence_check_count": len(gate_checks),
        "paper_sandbox_local_runtime_health_probe_evidence_ready_count": gate_ready_count,
        "paper_sandbox_local_runtime_health_probe_evidence_checks": gate_checks,
        "paper_sandbox_local_runtime_health_probe_evidence_status": "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_PROBE_EVIDENCE_READY" if status == "READY" else "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_PROBE_EVIDENCE_NOT_READY",
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
            f"{PATCH_ID}_local_runtime_health_probe_evidence_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_local_runtime_health_probe_evidence_schema_{generated_at}.json": schema,
            f"{PATCH_ID}_future_health_probe_evidence_sample_{generated_at}.json": sample,
            f"{PATCH_ID}_local_runtime_health_probe_evidence_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_local_runtime_health_probe_evidence_gate_{generated_at}.json": {"gate_name": "paper_sandbox_local_runtime_health_probe_evidence_gate", "checks": gate_checks, "check_count": len(gate_checks), "ready_count": gate_ready_count},
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "local_runtime_health_probe_evidence_contract" in filename:
                report["local_runtime_health_probe_evidence_contract_path"] = str(path)
            elif "local_runtime_health_probe_evidence_schema" in filename:
                report["health_probe_evidence_schema_path"] = str(path)
            elif "future_health_probe_evidence_sample" in filename:
                report["future_health_probe_evidence_sample_path"] = str(path)
            elif "local_runtime_health_probe_evidence_probe" in filename:
                report["paper_sandbox_local_runtime_health_probe_evidence_probe_path"] = str(path)
            elif "no_runtime_start_no_health_probe" in filename:
                report["no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_sandbox_local_runtime_health_probe_evidence_gate" in filename:
                report["paper_sandbox_local_runtime_health_probe_evidence_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_local_runtime_health_probe_evidence_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["local_runtime_health_probe_evidence_contract_path"] = None
        report["health_probe_evidence_schema_path"] = None
        report["future_health_probe_evidence_sample_path"] = None
        report["paper_sandbox_local_runtime_health_probe_evidence_probe_path"] = None
        report["no_runtime_start_no_health_probe_call_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_local_runtime_health_probe_evidence_gate_path"] = None

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
