from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436639G"
PATCH_VERSION = "4B.4.3.6.6.39G"
PATCH_NAME = "Paper Sandbox Runtime Transition Closure"
READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_TRANSITION_CLOSURE_READY_"
    "RUNTIME_TRANSITION_CLOSED_PAPER_RUNTIME_NOT_STARTED_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_TRANSITION_CLOSURE_NOT_READY_"
    "PAPER_RUNTIME_NOT_STARTED_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_OBSERVATION_RUNTIME_METRICS_READY_"
    "METRICS_CONTRACT_RUNTIME_NOT_STARTED_BY_PATCH_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.40A"
NEXT_PHASE_NAME = "Paper Sandbox Runtime Start Execution Authorization Review"
CLOSURE_SCOPE = "paper_sandbox_runtime_transition_closure_review_only"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_observation_runtime_metrics_ready": True,
    "approved_for_paper_sandbox_observation_runtime_metrics": True,
    "approved_for_observation_runtime_metrics_contract": True,
    "observation_runtime_metrics_contract_ready": True,
    "observation_runtime_metrics_contract_only": True,
    "observation_runtime_metrics_schema_declared": True,
    "future_observation_runtime_metrics_sample_declared": True,
    "observation_runtime_metrics_collection_deferred": True,
    "observation_runtime_metrics_collection_performed": False,
    "observation_runtime_metrics_collection_performed_by_patch": False,
    "runtime_metrics_collection_allowed": False,
    "runtime_metrics_collection_performed": False,
    "runtime_still_not_started_by_patch": True,
    "runtime_process_started": False,
    "runtime_process_status": "NOT_STARTED_BY_39F",
    "runtime_start_performed": False,
    "runtime_health_endpoint_called": False,
    "runtime_health_probe_performed": False,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_command_execution_allowed": False,
    "runtime_start_command_allowed": False,
    "approved_for_paper_runtime_start": False,
    "paper_runtime_start_allowed": False,
    "paper_runtime_start_performed": False,
    "paper_order_submit_allowed": False,
    "paper_order_submit_performed": False,
    "network_order_submit_allowed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_submit_performed": False,
    "exchange_submit_performed": False,
    "approved_for_paper_transition": False,
    "paper_transition_blocked": True,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "private_api_access_allowed": False,
    "signed_request_performed": False,
    "final_safety_violation_count": 0,
}


@dataclass(frozen=True)
class Source39FStatus:
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


def _is_main_39f_ready_report(path: Path) -> bool:
    name = path.name
    prefix = "4B436639F_paper_sandbox_observation_runtime_metrics_"
    if not name.startswith(prefix) or not name.endswith("_ready.json"):
        return False
    excluded_tokens = (
        "_not_ready",
        "_probe_",
        "_contract_",
        "_schema_",
        "_sample_",
        "_guard_",
        "_gate_",
        "_closure_",
        "_transition_",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    candidates = [
        path
        for path in reports_dir.glob("4B436639F_paper_sandbox_observation_runtime_metrics_*_ready.json")
        if _is_main_39f_ready_report(path)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def validate_source_39f(reports_dir: Path) -> Source39FStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source39FStatus(
            complete=False,
            status="SOURCE_39F_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_39f_ready_report"],
            errors=[f"39F READY report not found under {reports_dir}"],
            data={},
        )
    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover
        return Source39FStatus(
            complete=False,
            status="SOURCE_39F_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_39f_json"],
            errors=[str(exc)],
            data={},
        )
    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")
    complete = not errors
    return Source39FStatus(
        complete=complete,
        status="SOURCE_39F_READY" if complete else "SOURCE_39F_NOT_READY",
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


def build_transition_closure_contract(source: Source39FStatus, generated_at_utc: str) -> dict[str, Any]:
    rules = [
        _rule("source_39f_ready_required", "39F READY observation runtime metrics contract evidence is required"),
        _rule("runtime_transition_closure_only", "39G closes the paper sandbox runtime transition review only"),
        _rule("paper_runtime_start_remains_not_approved", "paper runtime start remains not approved"),
        _rule("paper_runtime_process_not_started", "paper runtime process remains not started"),
        _rule("runtime_start_command_not_executed", "runtime start command remains unexecuted"),
        _rule("health_probe_not_performed", "runtime health probe remains not performed"),
        _rule("observation_metrics_not_collected", "observation runtime metrics remain not collected by patch"),
        _rule("paper_order_submit_forbidden", "paper order submit remains forbidden"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39G cannot collect network market data"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        _rule("next_phase_not_auto_unlocked", "40A is not auto-unlocked by 39G"),
    ]
    contract = {
        "contract_name": "paper_sandbox_runtime_transition_closure_contract",
        "scope": CLOSURE_SCOPE,
        "mode": "RUNTIME_TRANSITION_CLOSURE_NO_RUNTIME_START_NO_NETWORK_ORDER",
        "generated_at_utc": generated_at_utc,
        "reviewed_source_patch": "4B.4.3.6.6.39F",
        "source_report": source.report_path,
        "paper_runtime_start_approved": False,
        "paper_runtime_start_performed": False,
        "runtime_process_started": False,
        "runtime_start_command_executed": False,
        "runtime_health_probe_performed": False,
        "observation_runtime_metrics_collection_performed": False,
        "network_order_submit_allowed": False,
        "live_environment_enabled": False,
        "exchange_submit_allowed": False,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_transition_closure_summary(source: Source39FStatus, generated_at_utc: str) -> dict[str, Any]:
    summary = {
        "summary_name": "paper_sandbox_runtime_transition_closure_summary",
        "scope": CLOSURE_SCOPE,
        "generated_at_utc": generated_at_utc,
        "source_report": source.report_path,
        "source_39f_status": source.status,
        "phase_39_runtime_transition_closed": source.complete,
        "runtime_started_during_phase_39": False,
        "runtime_start_command_executed_during_phase_39": False,
        "health_probe_collected_during_phase_39": False,
        "observation_runtime_metrics_collected_during_phase_39": False,
        "network_order_submitted_during_phase_39": False,
        "live_real_enabled_during_phase_39": False,
        "exchange_submit_performed_during_phase_39": False,
        "next_phase_unlock_allowed": False,
    }
    summary["digest"] = stable_digest(summary)
    return summary


def build_transition_closure_probe(source: Source39FStatus) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_39f_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False},
        {"probe_id": "runtime_transition_closure_declared", "expected": True, "result": True, "passed": True},
        {"probe_id": "paper_runtime_start_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_process_not_started", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_start_command_not_executed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "observation_runtime_metrics_collection_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "network_order_submit_allowed": False},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_market_data_collection_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "signed_request_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "private_api_access_not_allowed", "expected": False, "result": False, "passed": True},
        {"probe_id": "runtime_overlay_not_activated", "expected": False, "result": False, "passed": True},
        {"probe_id": "training_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "reload_not_performed", "expected": False, "result": False, "passed": True},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True},
    ]
    probe = {
        "probe_name": "paper_sandbox_runtime_transition_closure_probe",
        "probe_mode": "RUNTIME_TRANSITION_CLOSURE_NO_RUNTIME_START_NO_NETWORK_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_runtime_no_submit_guard() -> dict[str, Any]:
    rules = [
        _rule("closure_only", "39G only closes the runtime transition review"),
        _rule("runtime_process_start_forbidden", "39G cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "39G cannot perform runtime health probes"),
        _rule("runtime_start_command_execution_forbidden", "39G cannot execute runtime start command"),
        _rule("observation_metrics_collection_forbidden", "39G cannot collect observation runtime metrics"),
        _rule("paper_runtime_start_forbidden", "39G cannot perform paper runtime start"),
        _rule("paper_order_submit_forbidden", "39G cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("network_market_data_collection_forbidden", "39G cannot collect network market data"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        _rule("git_mutation_forbidden", "git mutating operations are not performed"),
    ]
    guard = {
        "guard_name": "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard",
        "status": "NO_RUNTIME_START_NO_OBSERVATION_METRICS_COLLECTION_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_CLOSURE_GUARD_READY",
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    guard["digest"] = stable_digest(guard)
    return guard


def build_report(reports_dir: Path | str = Path("reports/recovery"), *, write_artifacts: bool = False) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    source = validate_source_39f(reports_path)
    generated_at = utc_stamp()
    contract = build_transition_closure_contract(source, generated_at)
    summary = build_transition_closure_summary(source, generated_at)
    probe = build_transition_closure_probe(source)
    guard = build_no_runtime_no_submit_guard()

    gate_checks = [
        _check("source_39f_ready", source.complete),
        _check("observation_runtime_metrics_ready", source.data.get("paper_sandbox_observation_runtime_metrics_ready") is True),
        _check("runtime_transition_closure_contract_locked"),
        _check("runtime_transition_closure_summary_declared"),
        _check("paper_runtime_start_not_approved"),
        _check("paper_runtime_start_not_performed"),
        _check("runtime_start_command_not_executed"),
        _check("runtime_process_not_started"),
        _check("runtime_health_probe_not_performed"),
        _check("observation_runtime_metrics_collection_not_performed"),
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
        _check("closure_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("safety_flags_clean"),
    ]
    gate_ready_count = sum(1 for item in gate_checks if item["ready"])
    final_safety_violations = [] if source.complete else list(source.errors)
    status = "READY" if source.complete and gate_ready_count == len(gate_checks) else "NOT_READY"

    report: dict[str, Any] = {
        "ok": status == "READY",
        "status": status,
        "decision": READY_DECISION if status == "READY" else NOT_READY_DECISION,
        "generated_at_utc": generated_at,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "source_report": source.report_path,
        "source_39f_report": source.report_path,
        "source_39f_complete": source.complete,
        "source_39f_status": source.status,
        "source_39f_decision": source.decision,
        "source_39f_safety_violation_count": source.safety_violation_count,
        "source_39f_safety_violations": source.safety_violations,
        "source_39f_errors": source.errors,
        "source_39f_approved_for_paper_runtime_start": source.data.get("approved_for_paper_runtime_start", False),
        "source_39f_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_39f_runtime_start_command_executed": source.data.get("runtime_start_command_executed", False),
        "source_39f_observation_runtime_metrics_collection_performed": source.data.get("observation_runtime_metrics_collection_performed", False),
        "source_39f_runtime_health_probe_performed": source.data.get("runtime_health_probe_performed", False),
        "phase_39_runtime_transition_closure_review": True,
        "phase_39_runtime_transition_closed": status == "READY",
        "phase_39_planning_only": True,
        "phase_39_execution_started": False,
        "phase_39_unlocked": False,
        "paper_sandbox_runtime_transition_closure_complete": status == "READY",
        "paper_sandbox_runtime_transition_closure_locked": True,
        "paper_sandbox_runtime_transition_closure_ready": status == "READY",
        "paper_sandbox_runtime_transition_closure_status": "PAPER_SANDBOX_RUNTIME_TRANSITION_CLOSURE_READY" if status == "READY" else "PAPER_SANDBOX_RUNTIME_TRANSITION_CLOSURE_NOT_READY",
        "paper_sandbox_runtime_transition_closure_mode": "RUNTIME_TRANSITION_CLOSURE_NO_RUNTIME_START_NO_NETWORK_ORDER",
        "runtime_transition_closure_complete": True,
        "runtime_transition_closure_locked": True,
        "runtime_transition_closure_ready": status == "READY",
        "runtime_transition_closure_only": True,
        "runtime_transition_closed": status == "READY",
        "runtime_transition_closure_contract_complete": True,
        "runtime_transition_closure_contract_locked": True,
        "runtime_transition_closure_contract_ready": status == "READY",
        "runtime_transition_closure_contract_rule_count": contract["rule_count"],
        "runtime_transition_closure_contract_ready_count": contract["ready_count"],
        "runtime_transition_closure_contract_rules": contract["rules"],
        "runtime_transition_closure_contract_digest": contract["digest"],
        "runtime_transition_closure_summary": summary,
        "runtime_transition_closure_summary_declared": True,
        "runtime_transition_closure_summary_digest": summary["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_runtime_transition_closure": status == "READY",
        "approved_for_runtime_transition_closure": status == "READY",
        "approved_for_observation_runtime_metrics_contract": True,
        "approved_for_paper_runtime_start": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_required": True,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "RUNTIME_TRANSITION_CLOSURE_READY_NO_RUNTIME_PROCESS_NO_ORDER",
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_approval_performed": False,
        "paper_runtime_start_approval_ready": False,
        "paper_runtime_start_authorization_performed": False,
        "paper_runtime_start_authorization_ready": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "paper_submit_allowed": False,
        "observation_runtime_metrics_collection_deferred": True,
        "observation_runtime_metrics_collection_performed": False,
        "observation_runtime_metrics_collection_performed_by_patch": False,
        "runtime_metrics_collection_allowed": False,
        "runtime_metrics_collection_performed": False,
        "runtime_still_not_started_by_patch": True,
        "runtime_process_status": "NOT_STARTED_BY_39G",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_39g": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "runtime_start_performed": False,
        "runtime_start_command_template": source.data.get("runtime_start_command_template"),
        "runtime_start_command_template_preserved": source.data.get("runtime_start_command_template") is not None,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_declared_only": True,
        "runtime_start_command_review_only": True,
        "runtime_start_command_allowed": False,
        "runtime_start_command_execution_allowed": False,
        "runtime_start_command_executed": False,
        "runtime_start_command_execution_performed": False,
        "runtime_health_endpoint_called": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_39g": True,
        "runtime_health_probe_deferred_to_future_runtime": True,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "network_market_data_collection_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "order_submit_performed": False,
        "approved_for_live_real": False,
        "live_environment_enabled": False,
        "live_transition_ready": False,
        "live_transition_allowed": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
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
        "paper_sandbox_runtime_transition_closure_probe_complete": True,
        "paper_sandbox_runtime_transition_closure_probe_locked": True,
        "paper_sandbox_runtime_transition_closure_probe_mode": probe["probe_mode"],
        "paper_sandbox_runtime_transition_closure_probe_count": probe["probe_count"],
        "paper_sandbox_runtime_transition_closure_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_runtime_transition_closure_probes": probe["probes"],
        "paper_sandbox_runtime_transition_closure_probe_digest": probe["digest"],
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_complete": True,
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_locked": True,
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_status": guard["status"],
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_rule_count": guard["rule_count"],
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_ready_count": guard["ready_count"],
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_rules": guard["rules"],
        "no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_digest": guard["digest"],
        "paper_sandbox_runtime_transition_closure_check_complete": True,
        "paper_sandbox_runtime_transition_closure_check_locked": True,
        "paper_sandbox_runtime_transition_closure_check_count": len(gate_checks),
        "paper_sandbox_runtime_transition_closure_ready_count": gate_ready_count,
        "paper_sandbox_runtime_transition_closure_checks": gate_checks,
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
            f"{PATCH_ID}_runtime_transition_closure_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_runtime_transition_closure_summary_{generated_at}.json": summary,
            f"{PATCH_ID}_runtime_transition_closure_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_runtime_transition_closure_gate_{generated_at}.json": {"gate_name": "paper_sandbox_runtime_transition_closure_gate", "checks": gate_checks, "check_count": len(gate_checks), "ready_count": gate_ready_count},
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "runtime_transition_closure_contract" in filename:
                report["runtime_transition_closure_contract_path"] = str(path)
            elif "runtime_transition_closure_summary" in filename:
                report["runtime_transition_closure_summary_path"] = str(path)
            elif "runtime_transition_closure_probe" in filename:
                report["paper_sandbox_runtime_transition_closure_probe_path"] = str(path)
            elif "closure_guard" in filename:
                report["no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_path"] = str(path)
            elif "paper_sandbox_runtime_transition_closure_gate" in filename:
                report["paper_sandbox_runtime_transition_closure_gate_path"] = str(path)
        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_runtime_transition_closure_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["runtime_transition_closure_contract_path"] = None
        report["runtime_transition_closure_summary_path"] = None
        report["paper_sandbox_runtime_transition_closure_probe_path"] = None
        report["no_runtime_start_no_observation_metrics_collection_no_network_order_no_live_no_exchange_submit_closure_guard_path"] = None
        report["paper_sandbox_runtime_transition_closure_gate_path"] = None

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


if __name__ == "__main__":
    raise SystemExit(main())
