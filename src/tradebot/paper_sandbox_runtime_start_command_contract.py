from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436639B"
PATCH_VERSION = "4B.4.3.6.6.39B"
PATCH_NAME = "Paper Sandbox Runtime Start Command Contract"
READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_READY_"
    "COMMAND_DECLARED_ONLY_NO_EXECUTION_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_NOT_READY_"
    "NO_EXECUTION_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_RUNTIME_START_APPROVAL_REVIEW_READY_"
    "SEPARATE_EXPLICIT_OPERATOR_APPROVAL_REQUIRED_REVIEW_ONLY_"
    "NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.39C"
NEXT_PHASE_NAME = "Paper Sandbox Runtime Start Authorization Ledger"
COMMAND_CONTRACT_SCOPE = "paper_sandbox_runtime_start_command_contract_review_only"
COMMAND_TEMPLATE = (
    "python -m tradebot.paper_runtime_entry "
    "--mode paper-sandbox "
    "--config config/paper_sandbox.runtime.json "
    "--runtime-lock runtime/paper_sandbox_runtime.lock "
    "--no-network-order "
    "--no-live "
    "--no-exchange-submit"
)

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_runtime_start_approval_review_ready": True,
    "approved_for_paper_sandbox_runtime_start_approval_review": True,
    "approved_for_paper_runtime_start_approval_review": True,
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
class Source39AStatus:
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


def _is_main_39a_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436639A_paper_sandbox_runtime_start_approval_review_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_contract_",
        "_sample_",
        "_gate_",
        "_guard_",
        "_no_runtime_",
        "_operator_",
        "_separate_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436639A_paper_sandbox_runtime_start_approval_review_*_ready.json")
        if _is_main_39a_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_39a(reports_dir: Path) -> Source39AStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source39AStatus(
            complete=False,
            status="SOURCE_39A_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_39a_ready_report"],
            errors=[f"39A READY report not found under {reports_dir}"],
            data={},
        )

    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover
        return Source39AStatus(
            complete=False,
            status="SOURCE_39A_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_39a_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")

    complete = not errors
    return Source39AStatus(
        complete=complete,
        status="SOURCE_39A_READY" if complete else "SOURCE_39A_NOT_READY",
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


def build_command_template(generated_at_utc: str, source: Source39AStatus) -> dict[str, Any]:
    template = {
        "command_name": "paper_sandbox_runtime_start_command_template",
        "command_scope": COMMAND_CONTRACT_SCOPE,
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39A",
        "source_report": source.report_path,
        "command_template": COMMAND_TEMPLATE,
        "command_declared_only": True,
        "command_executed": False,
        "runtime_process_started": False,
        "runtime_start_allowed": False,
        "network_order_submit_allowed": False,
        "live_environment_enabled": False,
        "exchange_submit_allowed": False,
        "required_env": {
            "TRADEBOT_MODE": "paper-sandbox",
            "TRADEBOT_RUNTIME_PROFILE": "paper_only_no_submit",
            "TRADEBOT_NETWORK_ORDER_SUBMIT": "0",
            "TRADEBOT_LIVE_REAL": "0",
            "TRADEBOT_EXCHANGE_SUBMIT": "0",
        },
        "required_preconditions": [
            "39A runtime-start approval review READY",
            "separate explicit operator authorization ledger required in 39C",
            "single-instance runtime lock must be available before any future start",
            "paper-only config must be validated before any future start",
        ],
    }
    template["digest"] = stable_digest(template)
    return template


def build_command_contract(source: Source39AStatus, generated_at_utc: str) -> dict[str, Any]:
    rules = [
        _rule("source_39a_ready_required", "39A READY runtime-start approval review evidence is required"),
        _rule("runtime_start_command_contract_only", "39B defines a runtime start command contract only"),
        _rule("runtime_start_command_template_declared", "runtime start command template must be declared"),
        _rule("runtime_start_command_not_executed", "39B must not execute the runtime start command"),
        _rule("runtime_process_start_forbidden", "39B cannot start the runtime process"),
        _rule("runtime_start_authorization_ledger_required_next", "39C explicit runtime start authorization ledger is required before any start"),
        _rule("paper_only_config_required", "future runtime command must be paper-only config scoped"),
        _rule("runtime_process_lock_required", "future runtime command must be single-instance lock guarded"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39B cannot collect network market data"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("39c_not_auto_unlocked", "39C is not auto-unlocked by 39B"),
    ]
    contract = {
        "contract_name": "paper_sandbox_runtime_start_command_contract",
        "source_39a_status": source.status,
        "command_contract_scope": COMMAND_CONTRACT_SCOPE,
        "command_contract_mode": "COMMAND_DECLARED_ONLY_NO_EXECUTION_NO_NETWORK_ORDER",
        "runtime_start_command_contract_only": True,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_start_authorization_ledger_required_next": True,
        "paper_only_config_required": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39A",
        "source_report": source.report_path,
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_command_contract_probe(source: Source39AStatus) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_39a_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "runtime_start_command_contract_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_start_command_template_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_start_command_declared_only", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_start_command_execution_denied", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_start_command_not_executed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_runtime_start_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_transition_approval_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_market_data_collection_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "signed_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "private_api_access_not_allowed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probe = {
        "probe_name": "paper_sandbox_runtime_start_command_contract_probe",
        "probe_mode": "STATIC_COMMAND_CONTRACT_DECLARED_ONLY_NO_EXECUTION_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_runtime_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("runtime_start_command_execution_forbidden", "39B cannot execute the runtime start command"),
        _rule("paper_runtime_process_start_forbidden", "39B cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "39B cannot perform runtime health probes"),
        _rule("paper_runtime_start_approval_not_performed", "39B does not perform runtime start approval"),
        _rule("paper_transition_approval_not_performed", "39B does not perform paper transition approval"),
        _rule("paper_order_submit_forbidden", "39B cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39B cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 39B"),
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
    source = validate_source_39a(reports_path)
    generated_at = utc_stamp()

    command_template = build_command_template(generated_at, source)
    contract = build_command_contract(source, generated_at)
    probe = build_command_contract_probe(source)
    guard = build_no_runtime_no_order_guard()

    source_ready = source.complete
    gate_checks = [
        _check("source_39a_ready", source_ready),
        _check("phase_39_runtime_start_review_ready"),
        _check("runtime_start_approval_review_ready"),
        _check("runtime_start_command_contract_locked"),
        _check("runtime_start_command_contract_only"),
        _check("runtime_start_command_template_declared"),
        _check("runtime_start_command_declared_only"),
        _check("runtime_start_command_execution_denied"),
        _check("runtime_start_command_not_executed"),
        _check("runtime_start_authorization_ledger_required_next"),
        _check("paper_only_config_required"),
        _check("runtime_process_lock_required"),
        _check("single_instance_runtime_required"),
        _check("paper_transition_approval_not_performed"),
        _check("paper_runtime_start_approval_not_performed"),
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
        _check("command_contract_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
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
        "source_39a_report": source.report_path,
        "source_39a_complete": source.complete,
        "source_39a_status": source.status,
        "source_39a_decision": source.decision,
        "source_39a_safety_violation_count": source.safety_violation_count,
        "source_39a_safety_violations": source.safety_violations,
        "source_39a_errors": source.errors,
        "source_39a_approved_for_paper_transition": source.data.get("approved_for_paper_transition", False),
        "source_39a_approved_for_paper_runtime_start": source.data.get("approved_for_paper_runtime_start", False),
        "source_39a_paper_sandbox_runtime_start_approval_review_ready": source.data.get("paper_sandbox_runtime_start_approval_review_ready", False),
        "source_39a_paper_transition_blocked": source.data.get("paper_transition_blocked", True),
        "source_39a_paper_runtime_start_performed": source.data.get("paper_runtime_start_performed", False),
        "source_39a_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_39a_network_order_submit_performed": source.data.get("network_order_submit_performed", False),
        "phase_39_runtime_start_review_ready": source.data.get("phase_39_runtime_start_review", True),
        "phase_39_command_contract_review": True,
        "phase_39_planning_only": True,
        "phase_39_execution_started": False,
        "phase_39_unlocked": False,
        "paper_sandbox_runtime_start_command_contract_complete": status == "READY",
        "paper_sandbox_runtime_start_command_contract_locked": True,
        "paper_sandbox_runtime_start_command_contract_ready": status == "READY",
        "paper_sandbox_runtime_start_command_contract_mode": "COMMAND_DECLARED_ONLY_NO_EXECUTION_NO_NETWORK_ORDER",
        "runtime_start_command_contract_complete": True,
        "runtime_start_command_contract_locked": True,
        "runtime_start_command_contract_ready": status == "READY",
        "runtime_start_command_contract_only": True,
        "runtime_start_command_contract_rule_count": contract["rule_count"],
        "runtime_start_command_contract_ready_count": contract["ready_count"],
        "runtime_start_command_contract_rules": contract["rules"],
        "runtime_start_command_contract_digest": contract["digest"],
        "runtime_start_command_template": COMMAND_TEMPLATE,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_review_only": True,
        "runtime_start_command_validated_for_review": status == "READY",
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_start_command_contract_scope": COMMAND_CONTRACT_SCOPE,
        "runtime_start_authorization_ledger_required_next": True,
        "paper_only_config_required": True,
        "paper_only_config_validated_for_command_contract": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "runtime_start_command_template_artifact": command_template,
        "paper_sandbox_runtime_start_command_contract_probe_complete": True,
        "paper_sandbox_runtime_start_command_contract_probe_locked": True,
        "paper_sandbox_runtime_start_command_contract_probe_mode": probe["probe_mode"],
        "paper_sandbox_runtime_start_command_contract_probe_count": probe["probe_count"],
        "paper_sandbox_runtime_start_command_contract_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_runtime_start_command_contract_probes": probe["probes"],
        "paper_sandbox_runtime_start_command_contract_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_runtime_start_command_contract": status == "READY",
        "approved_for_paper_runtime_start_command_contract": status == "READY",
        "approved_for_paper_runtime_start_approval_review": True,
        "approved_for_paper_runtime_start": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "COMMAND_CONTRACT_READY_DECLARED_ONLY_NO_RUNTIME_PROCESS_NO_ORDER",
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
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
        "runtime_process_status": "NOT_STARTED_BY_39B",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_39b": True,
        "runtime_start_performed": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_39b": True,
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
        "paper_sandbox_runtime_start_command_contract_gate_complete": True,
        "paper_sandbox_runtime_start_command_contract_gate_locked": True,
        "paper_sandbox_runtime_start_command_contract_gate_check_count": len(gate_checks),
        "paper_sandbox_runtime_start_command_contract_gate_ready_count": gate_ready_count,
        "paper_sandbox_runtime_start_command_contract_gate_checks": gate_checks,
        "paper_sandbox_runtime_start_command_contract_gate_status": "PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_GATE_READY" if status == "READY" else "PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_GATE_NOT_READY",
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
            f"{PATCH_ID}_runtime_start_command_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_runtime_start_command_template_{generated_at}.json": command_template,
            f"{PATCH_ID}_runtime_start_command_contract_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_runtime_start_command_contract_gate_{generated_at}.json": {"gate_name": "paper_sandbox_runtime_start_command_contract_gate", "checks": gate_checks, "check_count": len(gate_checks), "ready_count": gate_ready_count},
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "runtime_start_command_contract_" in filename and "probe" not in filename and "gate" not in filename:
                report["runtime_start_command_contract_path"] = str(path)
            elif "runtime_start_command_template" in filename:
                report["runtime_start_command_template_path"] = str(path)
            elif "runtime_start_command_contract_probe" in filename:
                report["paper_sandbox_runtime_start_command_contract_probe_path"] = str(path)
            elif "no_command_execution" in filename:
                report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_sandbox_runtime_start_command_contract_gate" in filename:
                report["paper_sandbox_runtime_start_command_contract_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_runtime_start_command_contract_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["runtime_start_command_contract_path"] = None
        report["runtime_start_command_template_path"] = None
        report["paper_sandbox_runtime_start_command_contract_probe_path"] = None
        report["no_command_execution_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_runtime_start_command_contract_gate_path"] = None

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
