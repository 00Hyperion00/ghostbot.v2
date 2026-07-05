from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436638H"
PATCH_VERSION = "4B.4.3.6.6.38H"
PATCH_NAME = "Paper Sandbox Observation Metrics Gate"
READY_DECISION = (
    "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_READY_"
    "STATIC_OBSERVATION_METRICS_CONTRACT_NO_RUNTIME_PROCESS_START_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_NOT_READY_"
    "NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_EVIDENCE_READY_"
    "LOCAL_HEALTH_EVIDENCE_CONTRACT_NO_RUNTIME_PROCESS_START_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.38I"
NEXT_PHASE_NAME = "Paper Transition Final Approval Closure"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_local_runtime_health_evidence_ready": True,
    "approved_for_paper_sandbox_local_runtime_health_evidence": True,
    "paper_transition_blocked": True,
    "approved_for_paper_transition": False,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "runtime_process_started": False,
    "runtime_start_performed": False,
    "runtime_health_probe_performed": False,
    "network_order_submit_performed": False,
    "order_submit_performed": False,
    "exchange_submit_performed": False,
    "network_request_performed": False,
    "final_safety_violation_count": 0,
}


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


def _is_main_38g_health_report(path: Path) -> bool:
    name = path.name
    if not name.startswith("4B436638G_paper_sandbox_local_runtime_health_evidence_"):
        return False
    excluded_tokens = (
        "_gate_",
        "_probe_",
        "_contract_",
        "_snapshot_",
        "_guard_",
        "_not_ready",
    )
    return not any(token in name for token in excluded_tokens)


def find_latest_source_report(reports_dir: Path) -> Path | None:
    strict_ready = [
        path
        for path in reports_dir.glob("4B436638G_paper_sandbox_local_runtime_health_evidence_*_ready.json")
        if _is_main_38g_health_report(path)
    ]
    if strict_ready:
        return sorted(strict_ready, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]

    fallback = [
        path
        for path in reports_dir.glob("4B436638G_paper_sandbox_local_runtime_health_evidence_*.json")
        if _is_main_38g_health_report(path)
    ]
    if not fallback:
        return None
    return sorted(fallback, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


@dataclass(frozen=True)
class Source38GStatus:
    complete: bool
    status: str
    report_path: str | None
    decision: str | None
    safety_violation_count: int
    safety_violations: list[Any]
    errors: list[str]
    data: dict[str, Any]


def validate_source_38g(reports_dir: Path) -> Source38GStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source38GStatus(
            complete=False,
            status="SOURCE_38G_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_38g_ready_report"],
            errors=[f"38G READY report not found under {reports_dir}"],
            data={},
        )

    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover - defensive CLI path
        return Source38GStatus(
            complete=False,
            status="SOURCE_38G_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_38g_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")

    complete = not errors
    return Source38GStatus(
        complete=complete,
        status="SOURCE_38G_READY" if complete else "SOURCE_38G_NOT_READY",
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


def build_static_observation_metrics_contract(source: Source38GStatus) -> dict[str, Any]:
    rules = [
        _rule("source_38g_ready_required", "38G READY local health evidence is required"),
        _rule("static_observation_metrics_contract_only", "38H defines a static observation metrics contract only"),
        _rule("local_health_snapshot_required", "38G static local health snapshot must be referenced"),
        _rule("runtime_process_start_forbidden", "38H cannot start the runtime process"),
        _rule("runtime_health_probe_forbidden", "38H cannot run runtime health probes"),
        _rule("network_market_data_collection_forbidden", "38H cannot collect network market data"),
        _rule("observation_metrics_collection_forbidden", "38H cannot collect live observation metrics"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("38i_not_auto_unlocked", "38I is not auto-unlocked by 38H"),
    ]
    contract = {
        "contract_name": "paper_sandbox_static_observation_metrics_contract",
        "source_38g_status": source.status,
        "static_observation_metrics_contract_mode": "STATIC_CONTRACT_NO_RUNTIME_PROCESS_NO_NETWORK_ORDER",
        "static_observation_metrics_contract_only": True,
        "local_health_evidence_required": True,
        "local_health_snapshot_required": True,
        "observation_metrics_collection_forbidden_in_38h": True,
        "network_market_data_collection_forbidden_in_38h": True,
        "runtime_process_start_forbidden_in_38h": True,
        "runtime_health_probe_forbidden_in_38h": True,
        "network_order_submit_disabled_required": True,
        "live_environment_disabled_required": True,
        "exchange_submit_disabled_required": True,
        "signed_request_disabled_required": True,
        "private_api_access_disabled_required": True,
        "rules": rules,
        "rule_count": len(rules),
        "ready_count": sum(1 for item in rules if item["ready"]),
    }
    contract["digest"] = stable_digest(contract)
    return contract


def build_static_observation_metrics_snapshot(source: Source38GStatus, generated_at_utc: str) -> dict[str, Any]:
    metrics = [
        {"metric_id": "source_38g_ready", "ready": source.complete, "value": source.status},
        {"metric_id": "local_health_evidence_ready", "ready": True, "value": True},
        {"metric_id": "static_health_snapshot_available", "ready": True, "value": True},
        {"metric_id": "runtime_process_not_started", "ready": True, "value": False},
        {"metric_id": "runtime_health_probe_not_performed", "ready": True, "value": False},
        {"metric_id": "observation_metrics_collection_not_performed", "ready": True, "value": False},
        {"metric_id": "network_market_data_collection_not_performed", "ready": True, "value": False},
        {"metric_id": "network_order_submit_not_performed", "ready": True, "value": False},
        {"metric_id": "live_real_not_approved", "ready": True, "value": False},
        {"metric_id": "exchange_submit_not_performed", "ready": True, "value": False},
        {"metric_id": "final_safety_clean", "ready": source.safety_violation_count == 0, "value": source.safety_violation_count},
    ]
    snapshot = {
        "snapshot_name": "paper_sandbox_static_observation_metrics_snapshot",
        "snapshot_mode": "STATIC_OBSERVATION_METRICS_NO_RUNTIME_COLLECTION",
        "generated_at_utc": generated_at_utc,
        "source_report": source.report_path,
        "source_38g_status": source.status,
        "static_observation_metrics_snapshot_created": True,
        "static_observation_metrics_snapshot_locked": True,
        "static_observation_metrics_snapshot_ready": source.complete,
        "static_observation_metrics_only": True,
        "runtime_observation_metrics_collection_performed": False,
        "network_market_data_collection_performed": False,
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_health_probe_performed": False,
        "network_request_performed": False,
        "network_order_submit_performed": False,
        "paper_order_submit_performed": False,
        "exchange_submit_performed": False,
        "live_environment_enabled": False,
        "paper_environment_enabled": False,
        "observation_metric_items": metrics,
    }
    snapshot["observation_metric_item_count"] = len(metrics)
    snapshot["observation_metric_ready_count"] = sum(1 for item in metrics if item["ready"])
    snapshot["digest"] = stable_digest(snapshot)
    return snapshot


def build_observation_metrics_probe(source: Source38GStatus) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_38g_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False},
        {"probe_id": "static_observation_metrics_contract_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "static_observation_metrics_snapshot_created", "expected": "STATIC_OBSERVATION_METRICS_ONLY", "result": "STATIC_OBSERVATION_METRICS_ONLY", "passed": True, "runtime_start_allowed": False},
        {"probe_id": "observation_metrics_collection_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "network_market_data_collection_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_health_probe_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "runtime_health_endpoint_not_called", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "network_request_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "signed_request_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "private_api_access_not_allowed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "report_mutation_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False},
    ]
    probe = {
        "probe_name": "paper_sandbox_observation_metrics_gate_probe",
        "observation_metrics_probe_mode": "STATIC_OBSERVATION_METRICS_NO_RUNTIME_NO_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_runtime_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("paper_runtime_process_start_forbidden", "38H cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "38H cannot perform runtime health probes"),
        _rule("observation_metrics_collection_forbidden", "38H cannot collect live observation metrics"),
        _rule("network_market_data_collection_forbidden", "38H cannot collect network market data"),
        _rule("paper_order_submit_forbidden", "38H cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 38H"),
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
    source = validate_source_38g(reports_path)
    generated_at = utc_stamp()

    contract = build_static_observation_metrics_contract(source)
    snapshot = build_static_observation_metrics_snapshot(source, generated_at)
    probe = build_observation_metrics_probe(source)
    guard = build_no_runtime_no_order_guard()

    source_ready = source.complete
    gate_checks = [
        _check("source_38g_ready", source_ready),
        _check("phase_37_final_closed"),
        _check("paper_sandbox_local_runtime_health_evidence_ready"),
        _check("local_health_evidence_contract_available"),
        _check("static_observation_metrics_contract_locked"),
        _check("static_observation_metrics_snapshot_created"),
        _check("static_observation_metrics_only"),
        _check("observation_metrics_collection_forbidden"),
        _check("network_market_data_collection_forbidden"),
        _check("runtime_process_start_forbidden"),
        _check("runtime_health_probe_forbidden"),
        _check("runtime_health_endpoint_not_called"),
        _check("paper_transition_not_approved_by_patch"),
        _check("paper_runtime_not_started"),
        _check("paper_order_submit_forbidden"),
        _check("network_order_submit_forbidden"),
        _check("network_request_forbidden"),
        _check("live_real_remains_not_approved"),
        _check("exchange_submit_remains_forbidden"),
        _check("signed_request_forbidden"),
        _check("private_api_forbidden"),
        _check("runtime_overlay_training_reload_forbidden"),
        _check("git_mutating_operations_forbidden"),
        _check("report_mutation_forbidden"),
        _check("next_phase_not_auto_unlocked"),
        _check("safety_flags_clean"),
        _check("metrics_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("static_observation_metrics_ready", source_ready),
        _check("runtime_process_status_not_started"),
        _check("observation_metrics_contract_no_order"),
        _check("observation_metrics_contract_no_live"),
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
        "source_38g_report": source.report_path,
        "source_38g_complete": source.complete,
        "source_38g_status": source.status,
        "source_38g_decision": source.decision,
        "source_38g_safety_violation_count": source.safety_violation_count,
        "source_38g_safety_violations": source.safety_violations,
        "source_38g_errors": source.errors,
        "source_38g_approved_for_paper_transition": source.data.get("approved_for_paper_transition", False),
        "source_38g_paper_sandbox_local_runtime_health_evidence_ready": source.data.get("paper_sandbox_local_runtime_health_evidence_ready", False),
        "source_38g_paper_transition_blocked": source.data.get("paper_transition_blocked", True),
        "source_38g_runtime_process_started": source.data.get("runtime_process_started", False),
        "source_38g_runtime_health_probe_performed": source.data.get("runtime_health_probe_performed", False),
        "source_38g_network_order_submit_performed": source.data.get("network_order_submit_performed", False),
        "phase_37_final_closed": True,
        "phase_38_planning_only": True,
        "phase_38_execution_started": False,
        "phase_38_unlocked": False,
        "paper_sandbox_observation_metrics_gate_complete": status == "READY",
        "paper_sandbox_observation_metrics_gate_locked": True,
        "paper_sandbox_observation_metrics_gate_ready": status == "READY",
        "paper_sandbox_observation_metrics_gate_mode": "STATIC_OBSERVATION_METRICS_CONTRACT_NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER",
        "static_observation_metrics_contract_complete": True,
        "static_observation_metrics_contract_locked": True,
        "static_observation_metrics_contract_ready": status == "READY",
        "static_observation_metrics_contract_mode": contract["static_observation_metrics_contract_mode"],
        "static_observation_metrics_contract_rule_count": contract["rule_count"],
        "static_observation_metrics_contract_ready_count": contract["ready_count"],
        "static_observation_metrics_contract_rules": contract["rules"],
        "static_observation_metrics_contract_digest": contract["digest"],
        "static_observation_metrics_snapshot_complete": True,
        "static_observation_metrics_snapshot_locked": True,
        "static_observation_metrics_snapshot_ready": status == "READY",
        "static_observation_metrics_snapshot_created": True,
        "static_observation_metrics_snapshot_source": "STATIC_HEALTH_EVIDENCE_NO_RUNTIME_PROCESS_START",
        "static_observation_metrics_only": True,
        "observation_metrics_collection_performed": False,
        "observation_metrics_runtime_binding_performed": False,
        "observation_metrics_static_only": True,
        "observation_metric_item_count": snapshot["observation_metric_item_count"],
        "observation_metric_ready_count": snapshot["observation_metric_ready_count"],
        "observation_runtime_sample_count": 0,
        "observation_static_metric_count": snapshot["observation_metric_item_count"],
        "observation_min_sample_gate_mode": "CONTRACT_ONLY_NO_RUNTIME_COLLECTION",
        "network_market_data_collection_performed": False,
        "runtime_process_status": "NOT_STARTED_BY_38H",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_38h": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_38h": True,
        "runtime_health_endpoint_called": False,
        "paper_sandbox_observation_metrics_gate_probe_complete": True,
        "paper_sandbox_observation_metrics_gate_probe_locked": True,
        "paper_sandbox_observation_metrics_gate_probe_mode": probe["observation_metrics_probe_mode"],
        "paper_sandbox_observation_metrics_gate_probe_count": probe["probe_count"],
        "paper_sandbox_observation_metrics_gate_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_observation_metrics_gate_probes": probe["probes"],
        "paper_sandbox_observation_metrics_gate_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_observation_metrics_gate": status == "READY",
        "approved_for_paper_sandbox_local_runtime_health_evidence": True,
        "approved_for_paper_sandbox_local_runtime_activation_harness": True,
        "approved_for_paper_sandbox_runtime_activation_preflight": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_status": "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_READY_NO_RUNTIME_PROCESS_NO_ORDER",
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
        "runtime_start_performed": False,
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
        "paper_sandbox_observation_metrics_gate_check_complete": True,
        "paper_sandbox_observation_metrics_gate_check_locked": True,
        "paper_sandbox_observation_metrics_gate_check_count": len(gate_checks),
        "paper_sandbox_observation_metrics_gate_ready_count": gate_ready_count,
        "paper_sandbox_observation_metrics_gate_checks": gate_checks,
        "paper_sandbox_observation_metrics_gate_status": "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_READY" if status == "READY" else "PAPER_SANDBOX_OBSERVATION_METRICS_GATE_NOT_READY",
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
            f"{PATCH_ID}_static_observation_metrics_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_static_observation_metrics_snapshot_{generated_at}.json": snapshot,
            f"{PATCH_ID}_observation_metrics_gate_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_observation_metrics_gate_{generated_at}.json": {
                "gate_name": "paper_sandbox_observation_metrics_gate",
                "checks": gate_checks,
                "check_count": len(gate_checks),
                "ready_count": gate_ready_count,
            },
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            if "static_observation_metrics_contract" in filename:
                report["static_observation_metrics_contract_path"] = str(path)
            elif "static_observation_metrics_snapshot" in filename:
                report["static_observation_metrics_snapshot_path"] = str(path)
            elif "observation_metrics_gate_probe" in filename:
                report["paper_sandbox_observation_metrics_gate_probe_path"] = str(path)
            elif "no_runtime_process" in filename:
                report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "paper_sandbox_observation_metrics_gate" in filename:
                report["paper_sandbox_observation_metrics_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_observation_metrics_gate_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["static_observation_metrics_contract_path"] = None
        report["static_observation_metrics_snapshot_path"] = None
        report["paper_sandbox_observation_metrics_gate_probe_path"] = None
        report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_observation_metrics_gate_path"] = None

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
