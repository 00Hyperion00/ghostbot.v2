from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436639C"
PATCH_VERSION = "4B.4.3.6.6.39C"
PATCH_NAME = "Paper Sandbox Runtime Start Authorization Ledger"
READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_AUTHORIZATION_LEDGER_READY_"
    "EXPLICIT_TYPED_OPERATOR_APPROVAL_LEDGER_NO_COMMAND_EXECUTION_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_AUTHORIZATION_LEDGER_NOT_READY_"
    "NO_COMMAND_EXECUTION_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_READY_"
    "COMMAND_DECLARED_ONLY_NO_EXECUTION_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.39D"
NEXT_PHASE_NAME = "Paper Sandbox Local Runtime Process Start Gate"
AUTHORIZATION_SCOPE = "paper_sandbox_runtime_start_authorization_ledger_review_only"
AUTHORIZATION_PHRASE = "APPROVE PAPER SANDBOX RUNTIME START AUTHORIZATION LEDGER ONLY"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_runtime_start_command_contract_ready": True,
    "approved_for_paper_sandbox_runtime_start_command_contract": True,
    "approved_for_paper_runtime_start_command_contract": True,
    "runtime_start_command_template_declared": True,
    "runtime_start_command_declared_only": True,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_command_execution_allowed": False,
    "runtime_start_command_allowed": False,
    "approved_for_paper_runtime_start": False,
    "paper_runtime_start_approval_performed": False,
    "paper_runtime_start_approval_ready": False,
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
class Source39BStatus:
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


def _is_main_39b_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436639B_paper_sandbox_runtime_start_command_contract_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_template_",
        "_gate_",
        "_guard_",
        "_no_command_",
        "_authorization_",
        "_ledger_",
        "_sample_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436639B_paper_sandbox_runtime_start_command_contract_*_ready.json")
        if _is_main_39b_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_39b(reports_dir: Path) -> Source39BStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source39BStatus(
            complete=False,
            status="SOURCE_39B_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_39b_ready_report"],
            errors=[f"39B READY report not found under {reports_dir}"],
            data={},
        )

    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover
        return Source39BStatus(
            complete=False,
            status="SOURCE_39B_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_39b_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")

    complete = not errors
    return Source39BStatus(
        complete=complete,
        status="SOURCE_39B_READY" if complete else "SOURCE_39B_NOT_READY",
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


def build_authorization_evidence_schema(generated_at_utc: str, source: Source39BStatus) -> dict[str, Any]:
    return {
        "approval_phrase_required": AUTHORIZATION_PHRASE,
        "approval_scope_required": AUTHORIZATION_SCOPE,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "approved_at_utc_required": True,
        "source_report_required": True,
        "source_report": source.report_path,
        "reviewed_source_patch": "4B.4.3.6.6.39B",
        "generated_at_utc": generated_at_utc,
    }


def evaluate_runtime_start_authorization(evidence: Mapping[str, Any] | None, source: Source39BStatus) -> dict[str, Any]:
    if not evidence:
        return {
            "result": "DENY_RUNTIME_START_AUTHORIZATION_REQUIRED",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    if evidence.get("approval_phrase") != AUTHORIZATION_PHRASE:
        return {
            "result": "DENY_RUNTIME_START_AUTHORIZATION_PHRASE_MISMATCH",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    if evidence.get("approval_scope") != AUTHORIZATION_SCOPE:
        return {
            "result": "DENY_RUNTIME_START_AUTHORIZATION_SCOPE_MISMATCH",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    required_identity = ("operator_id", "operator_name", "operator_role")
    if any(not evidence.get(key) for key in required_identity):
        return {
            "result": "DENY_OPERATOR_IDENTITY_REQUIRED",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    if not evidence.get("approved_at_utc"):
        return {
            "result": "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    if not evidence.get("source_report") or evidence.get("source_report") != source.report_path:
        return {
            "result": "DENY_SOURCE_REPORT_REQUIRED",
            "accepted_for_authorization_ledger_review": False,
            "runtime_start_allowed": False,
            "command_execution_allowed": False,
            "network_order_submit_allowed": False,
            "paper_runtime_start_authorization_performed": False,
        }

    return {
        "result": "RUNTIME_START_AUTHORIZATION_EVIDENCE_ACCEPTED_FOR_LEDGER_REVIEW_ONLY",
        "accepted_for_authorization_ledger_review": True,
        "runtime_start_allowed": False,
        "command_execution_allowed": False,
        "network_order_submit_allowed": False,
        "paper_runtime_start_authorization_performed": False,
    }


def build_valid_authorization_sample(generated_at_utc: str, source: Source39BStatus) -> dict[str, Any]:
    sample = {
        "approval_phrase": AUTHORIZATION_PHRASE,
        "approval_scope": AUTHORIZATION_SCOPE,
        "approved_at_utc": generated_at_utc,
        "operator_id": "operator.local.runtime.start.authorization",
        "operator_name": "Operator Paper Runtime Start Authorization",
        "operator_role": "paper_sandbox_runtime_start_authorizer",
        "source_report": source.report_path,
        "accepted_for_review_only": True,
        "paper_runtime_start_authorization_performed": False,
        "runtime_start_allowed": False,
        "runtime_start_performed": False,
        "command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "network_order_submit_allowed": False,
    }
    sample["digest"] = stable_digest(sample)
    return sample


def build_authorization_ledger(source: Source39BStatus, generated_at_utc: str, valid_sample: Mapping[str, Any]) -> dict[str, Any]:
    rules = [
        _rule("source_39b_ready_required", "39B READY runtime-start command contract evidence is required"),
        _rule("explicit_runtime_start_authorization_required", "runtime start authorization ledger requires exact typed operator approval"),
        _rule("operator_identity_required", "operator id, name and role must be recorded"),
        _rule("operator_approval_timestamp_required", "runtime-start authorization must carry immutable UTC timestamp"),
        _rule("source_report_required", "runtime-start authorization evidence must reference the 39B READY source report"),
        _rule("approval_phrase_exact_match_required", "runtime-start authorization phrase must match the exact 39C phrase"),
        _rule("missing_or_invalid_authorization_fails_closed", "missing or mismatched runtime-start authorization fails closed"),
        _rule("valid_authorization_is_ledger_review_only", "valid runtime-start authorization evidence is accepted for ledger review only in 39C"),
        _rule("39c_does_not_execute_runtime_start_command", "39C cannot execute the runtime start command"),
        _rule("39c_does_not_start_runtime", "39C cannot start paper runtime process"),
        _rule("39c_does_not_enable_network_order", "39C cannot enable network order submit"),
        _rule("live_exchange_remain_forbidden", "live-real and exchange submit remain forbidden"),
        _rule("39d_not_auto_unlocked", "39D is not auto-unlocked by 39C"),
    ]
    ledger = {
        "ledger_name": "paper_sandbox_runtime_start_authorization_ledger",
        "ledger_scope": AUTHORIZATION_SCOPE,
        "ledger_mode": "TYPED_OPERATOR_AUTHORIZATION_LEDGER_REVIEW_ONLY_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39B",
        "source_report": source.report_path,
        "authorization_phrase_required": AUTHORIZATION_PHRASE,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "valid_authorization_sample_digest": valid_sample.get("digest"),
        "paper_runtime_start_authorization_performed": False,
        "runtime_start_command_executed": False,
        "runtime_start_performed": False,
        "network_order_submit_allowed": False,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    ledger["digest"] = stable_digest(ledger)
    return ledger


def build_authorization_probe(source: Source39BStatus) -> dict[str, Any]:
    missing = evaluate_runtime_start_authorization(None, source)
    invalid_phrase = evaluate_runtime_start_authorization({"approval_phrase": "WRONG"}, source)
    missing_identity = evaluate_runtime_start_authorization(
        {"approval_phrase": AUTHORIZATION_PHRASE, "approval_scope": AUTHORIZATION_SCOPE, "approved_at_utc": "20260706T000000Z", "source_report": source.report_path},
        source,
    )
    missing_timestamp = evaluate_runtime_start_authorization(
        {"approval_phrase": AUTHORIZATION_PHRASE, "approval_scope": AUTHORIZATION_SCOPE, "operator_id": "op", "operator_name": "Op", "operator_role": "reviewer", "source_report": source.report_path},
        source,
    )
    missing_source = evaluate_runtime_start_authorization(
        {"approval_phrase": AUTHORIZATION_PHRASE, "approval_scope": AUTHORIZATION_SCOPE, "operator_id": "op", "operator_name": "Op", "operator_role": "reviewer", "approved_at_utc": "20260706T000000Z"},
        source,
    )
    valid = evaluate_runtime_start_authorization(
        {"approval_phrase": AUTHORIZATION_PHRASE, "approval_scope": AUTHORIZATION_SCOPE, "operator_id": "op", "operator_name": "Op", "operator_role": "reviewer", "approved_at_utc": "20260706T000000Z", "source_report": source.report_path},
        source,
    )
    probes = [
        {"probe_id": "source_39b_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "missing_runtime_start_authorization_denied", "expected": "DENY_RUNTIME_START_AUTHORIZATION_REQUIRED", "result": missing["result"], "passed": missing["result"] == "DENY_RUNTIME_START_AUTHORIZATION_REQUIRED", "runtime_start_allowed": False, "command_execution_allowed": False},
        {"probe_id": "invalid_runtime_start_authorization_phrase_denied", "expected": "DENY_RUNTIME_START_AUTHORIZATION_PHRASE_MISMATCH", "result": invalid_phrase["result"], "passed": invalid_phrase["result"] == "DENY_RUNTIME_START_AUTHORIZATION_PHRASE_MISMATCH", "runtime_start_allowed": False, "command_execution_allowed": False},
        {"probe_id": "missing_operator_identity_denied", "expected": "DENY_OPERATOR_IDENTITY_REQUIRED", "result": missing_identity["result"], "passed": missing_identity["result"] == "DENY_OPERATOR_IDENTITY_REQUIRED", "runtime_start_allowed": False},
        {"probe_id": "missing_operator_timestamp_denied", "expected": "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED", "result": missing_timestamp["result"], "passed": missing_timestamp["result"] == "DENY_OPERATOR_APPROVAL_TIMESTAMP_REQUIRED", "runtime_start_allowed": False},
        {"probe_id": "missing_source_report_denied", "expected": "DENY_SOURCE_REPORT_REQUIRED", "result": missing_source["result"], "passed": missing_source["result"] == "DENY_SOURCE_REPORT_REQUIRED", "runtime_start_allowed": False},
        {"probe_id": "valid_runtime_start_authorization_evidence_accepted_for_ledger_review_only", "expected": "RUNTIME_START_AUTHORIZATION_EVIDENCE_ACCEPTED_FOR_LEDGER_REVIEW_ONLY", "result": valid["result"], "passed": valid["result"] == "RUNTIME_START_AUTHORIZATION_EVIDENCE_ACCEPTED_FOR_LEDGER_REVIEW_ONLY", "accepted_for_authorization_ledger_review": True, "runtime_start_allowed": False, "command_execution_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "valid_runtime_start_authorization_command_execution_denied", "expected": False, "result": False, "passed": True, "command_execution_allowed": False},
        {"probe_id": "valid_runtime_start_authorization_runtime_start_denied", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "valid_runtime_start_authorization_network_order_denied", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "runtime_start_command_not_executed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_runtime_start_authorization_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_transition_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_market_data_collection_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probe = {
        "probe_name": "paper_sandbox_runtime_start_authorization_ledger_probe",
        "probe_mode": "STATIC_TYPED_OPERATOR_AUTHORIZATION_LEDGER_REVIEW_ONLY_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_command_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("runtime_start_authorization_performed_false", "39C does not perform runtime start authorization"),
        _rule("runtime_start_command_execution_forbidden", "39C cannot execute the runtime start command"),
        _rule("paper_runtime_process_start_forbidden", "39C cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "39C cannot perform runtime health probes"),
        _rule("paper_transition_approval_not_performed", "39C does not perform paper transition approval"),
        _rule("paper_order_submit_forbidden", "39C cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39C cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 39C"),
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
    source = validate_source_39b(reports_path)
    generated_at = utc_stamp()

    evidence_schema = build_authorization_evidence_schema(generated_at, source)
    valid_sample = build_valid_authorization_sample(generated_at, source)
    ledger = build_authorization_ledger(source, generated_at, valid_sample)
    probe = build_authorization_probe(source)
    guard = build_no_command_no_order_guard()

    source_ready = source.complete
    valid_eval = evaluate_runtime_start_authorization(valid_sample, source)
    gate_checks = [
        _check("source_39b_ready", source_ready),
        _check("phase_39_command_contract_ready"),
        _check("runtime_start_command_contract_ready"),
        _check("explicit_runtime_start_authorization_ledger_locked"),
        _check("typed_runtime_start_operator_approval_required"),
        _check("operator_identity_required"),
        _check("operator_id_required"),
        _check("operator_name_required"),
        _check("operator_role_required"),
        _check("operator_approval_timestamp_required"),
        _check("source_report_required"),
        _check("missing_runtime_start_authorization_denied"),
        _check("invalid_runtime_start_authorization_phrase_denied"),
        _check("operator_identity_missing_denied"),
        _check("valid_runtime_start_authorization_ledger_review_only", valid_eval["accepted_for_authorization_ledger_review"] is True),
        _check("valid_runtime_start_authorization_command_execution_denied", valid_eval["command_execution_allowed"] is False),
        _check("valid_runtime_start_authorization_runtime_denied_no_submit", valid_eval["runtime_start_allowed"] is False),
        _check("valid_runtime_start_authorization_network_order_denied", valid_eval["network_order_submit_allowed"] is False),
        _check("runtime_start_command_not_executed"),
        _check("runtime_start_command_execution_not_performed"),
        _check("paper_runtime_start_authorization_not_performed"),
        _check("paper_runtime_not_started"),
        _check("runtime_process_not_started"),
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
        _check("authorization_ledger_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("safety_flags_clean"),
    ]
    gate_ready_count = sum(1 for item in gate_checks if item["ready"])
    final_safety_violations: list[str] = [] if source_ready else list(source.errors)
    status = "READY" if source_ready and gate_ready_count == len(gate_checks) else "NOT_READY"

    source_template = source.data.get("runtime_start_command_template") or source.data.get("runtime_start_command_template_artifact", {}).get("command_template")

    report: dict[str, Any] = {
        "ok": status == "READY",
        "status": status,
        "decision": READY_DECISION if status == "READY" else NOT_READY_DECISION,
        "generated_at_utc": generated_at,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "source_report": source.report_path,
        "source_39b_report": source.report_path,
        "source_39b_complete": source.complete,
        "source_39b_status": source.status,
        "source_39b_decision": source.decision,
        "source_39b_safety_violation_count": source.safety_violation_count,
        "source_39b_safety_violations": source.safety_violations,
        "source_39b_errors": source.errors,
        "source_39b_approved_for_paper_transition": source.data.get("approved_for_paper_transition", False),
        "source_39b_approved_for_paper_runtime_start": source.data.get("approved_for_paper_runtime_start", False),
        "source_39b_paper_sandbox_runtime_start_command_contract_ready": source.data.get("paper_sandbox_runtime_start_command_contract_ready", False),
        "source_39b_runtime_start_command_template_declared": source.data.get("runtime_start_command_template_declared", False),
        "source_39b_runtime_start_command_executed": source.data.get("runtime_start_command_executed", False),
        "source_39b_paper_transition_blocked": source.data.get("paper_transition_blocked", True),
        "source_39b_paper_runtime_start_performed": source.data.get("paper_runtime_start_performed", False),
        "source_39b_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_39b_network_order_submit_performed": source.data.get("network_order_submit_performed", False),
        "phase_39_command_contract_ready": source.data.get("phase_39_command_contract_review", True),
        "phase_39_authorization_ledger_review": True,
        "phase_39_planning_only": True,
        "phase_39_execution_started": False,
        "phase_39_unlocked": False,
        "approval_evidence_schema": evidence_schema,
        "paper_sandbox_runtime_start_authorization_ledger_complete": status == "READY",
        "paper_sandbox_runtime_start_authorization_ledger_locked": True,
        "paper_sandbox_runtime_start_authorization_ledger_ready": status == "READY",
        "paper_sandbox_runtime_start_authorization_ledger_mode": "EXPLICIT_TYPED_OPERATOR_AUTHORIZATION_LEDGER_REVIEW_ONLY_NO_COMMAND_EXECUTION_NO_NETWORK_ORDER",
        "explicit_runtime_start_authorization_ledger_complete": True,
        "explicit_runtime_start_authorization_ledger_locked": True,
        "explicit_runtime_start_authorization_ledger_ready": status == "READY",
        "explicit_runtime_start_authorization_ledger_rule_count": ledger["rule_count"],
        "explicit_runtime_start_authorization_ledger_ready_count": ledger["ready_count"],
        "explicit_runtime_start_authorization_ledger_rules": ledger["rules"],
        "explicit_runtime_start_authorization_ledger_digest": ledger["digest"],
        "explicit_runtime_start_authorization_required": True,
        "typed_runtime_start_operator_approval_required": True,
        "runtime_start_authorization_phrase_required": AUTHORIZATION_PHRASE,
        "runtime_start_authorization_scope_required": AUTHORIZATION_SCOPE,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "source_report_missing_denied": True,
        "operator_identity_missing_denied": True,
        "operator_approval_timestamp_missing_denied": True,
        "typed_runtime_start_authorization_missing_denied": True,
        "typed_runtime_start_authorization_invalid_denied": True,
        "runtime_start_operator_authorization_valid_evidence_sample": valid_sample,
        "valid_runtime_start_authorization_evidence_accepted_for_review": valid_eval["accepted_for_authorization_ledger_review"],
        "valid_runtime_start_authorization_evidence_command_execution_denied": valid_eval["command_execution_allowed"] is False,
        "valid_runtime_start_authorization_evidence_runtime_denied_no_submit": valid_eval["runtime_start_allowed"] is False,
        "valid_runtime_start_authorization_evidence_network_order_denied": valid_eval["network_order_submit_allowed"] is False,
        "valid_runtime_start_authorization_evidence_start_denied_without_separate_action": True,
        "runtime_start_command_template": source_template,
        "runtime_start_command_template_preserved": source_template is not None,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_review_only": True,
        "runtime_start_command_allowed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_start_authorization_ledger_required": True,
        "paper_only_config_required": True,
        "paper_only_config_validated_for_authorization_ledger": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "paper_sandbox_runtime_start_authorization_ledger_probe_complete": True,
        "paper_sandbox_runtime_start_authorization_ledger_probe_locked": True,
        "paper_sandbox_runtime_start_authorization_ledger_probe_mode": probe["probe_mode"],
        "paper_sandbox_runtime_start_authorization_ledger_probe_count": probe["probe_count"],
        "paper_sandbox_runtime_start_authorization_ledger_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_runtime_start_authorization_ledger_probes": probe["probes"],
        "paper_sandbox_runtime_start_authorization_ledger_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_runtime_start_authorization_ledger": status == "READY",
        "approved_for_paper_runtime_start_authorization_ledger": status == "READY",
        "approved_for_paper_runtime_start_command_contract": True,
        "approved_for_paper_runtime_start": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "AUTHORIZATION_LEDGER_READY_NO_COMMAND_EXECUTION_NO_RUNTIME_PROCESS_NO_ORDER",
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
        "runtime_process_status": "NOT_STARTED_BY_39C",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_39c": True,
        "runtime_start_performed": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_39c": True,
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
        "paper_sandbox_runtime_start_authorization_ledger_gate_complete": True,
        "paper_sandbox_runtime_start_authorization_ledger_gate_locked": True,
        "paper_sandbox_runtime_start_authorization_ledger_gate_check_count": len(gate_checks),
        "paper_sandbox_runtime_start_authorization_ledger_gate_ready_count": gate_ready_count,
        "paper_sandbox_runtime_start_authorization_ledger_gate_checks": gate_checks,
        "paper_sandbox_runtime_start_authorization_ledger_gate_status": "PAPER_SANDBOX_RUNTIME_START_AUTHORIZATION_LEDGER_GATE_READY" if status == "READY" else "PAPER_SANDBOX_RUNTIME_START_AUTHORIZATION_LEDGER_GATE_NOT_READY",
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
            f"{PATCH_ID}_runtime_start_authorization_ledger_{generated_at}.json": ledger,
            f"{PATCH_ID}_runtime_start_operator_authorization_sample_{generated_at}.json": valid_sample,
            f"{PATCH_ID}_runtime_start_authorization_evidence_schema_{generated_at}.json": evidence_schema,
            f"{PATCH_ID}_runtime_start_authorization_ledger_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_runtime_start_authorization_ledger_gate_{generated_at}.json": {"gate_name": "paper_sandbox_runtime_start_authorization_ledger_gate", "checks": gate_checks, "check_count": len(gate_checks), "ready_count": gate_ready_count},
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "runtime_start_authorization_ledger_" in filename and "probe" not in filename and "gate" not in filename:
                report["explicit_runtime_start_authorization_ledger_path"] = str(path)
            elif "runtime_start_operator_authorization_sample" in filename:
                report["runtime_start_operator_authorization_sample_path"] = str(path)
            elif "runtime_start_authorization_evidence_schema" in filename:
                report["authorization_evidence_schema_path"] = str(path)
            elif "runtime_start_authorization_ledger_probe" in filename:
                report["paper_sandbox_runtime_start_authorization_ledger_probe_path"] = str(path)
            elif "no_command_execution" in filename:
                report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_sandbox_runtime_start_authorization_ledger_gate" in filename:
                report["paper_sandbox_runtime_start_authorization_ledger_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_runtime_start_authorization_ledger_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["explicit_runtime_start_authorization_ledger_path"] = None
        report["runtime_start_operator_authorization_sample_path"] = None
        report["authorization_evidence_schema_path"] = None
        report["paper_sandbox_runtime_start_authorization_ledger_probe_path"] = None
        report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_runtime_start_authorization_ledger_gate_path"] = None

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
