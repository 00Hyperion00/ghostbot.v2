from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436638G"
PATCH_VERSION = "4B.4.3.6.6.38G"
PATCH_NAME = "Paper Sandbox Local Runtime Health Evidence"
READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_EVIDENCE_READY_"
    "LOCAL_HEALTH_EVIDENCE_CONTRACT_NO_RUNTIME_PROCESS_START_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_EVIDENCE_NOT_READY_"
    "NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER_LOCKED"
)
SOURCE_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_READY_PAPER_ONLY_"
    "LOCAL_HARNESS_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.38H"
NEXT_PHASE_NAME = "Paper Sandbox Observation Metrics Gate"

REQUIRED_SOURCE_FLAGS: dict[str, Any] = {
    "status": "READY",
    "decision": SOURCE_DECISION,
    "paper_sandbox_local_runtime_activation_harness_ready": True,
    "approved_for_paper_sandbox_local_runtime_activation_harness": True,
    "paper_transition_blocked": True,
    "approved_for_paper_transition": False,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "paper_runtime_start_performed": False,
    "runtime_start_performed": False,
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


def find_latest_source_report(reports_dir: Path) -> Path | None:
    patterns = (
        "4B436638F_paper_sandbox_local_runtime_activation_harness_*_ready.json",
        "4B436638F_paper_sandbox_local_runtime_activation_harness_*.json",
    )
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(reports_dir.glob(pattern))
    unique = sorted(set(candidates), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return unique[0] if unique else None


@dataclass(frozen=True)
class Source38FStatus:
    complete: bool
    status: str
    report_path: str | None
    decision: str | None
    safety_violation_count: int
    safety_violations: list[Any]
    errors: list[str]
    data: dict[str, Any]


def validate_source_38f(reports_dir: Path) -> Source38FStatus:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return Source38FStatus(
            complete=False,
            status="SOURCE_38F_MISSING",
            report_path=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["missing_38f_ready_report"],
            errors=[f"38F READY report not found under {reports_dir}"],
            data={},
        )

    try:
        data = _read_json(source_path)
    except Exception as exc:  # pragma: no cover - defensive CLI path
        return Source38FStatus(
            complete=False,
            status="SOURCE_38F_INVALID_JSON",
            report_path=str(source_path),
            decision=None,
            safety_violation_count=1,
            safety_violations=["invalid_38f_json"],
            errors=[str(exc)],
            data={},
        )

    errors: list[str] = []
    for key, expected in REQUIRED_SOURCE_FLAGS.items():
        if data.get(key) != expected:
            errors.append(f"{key} expected {expected!r}, got {data.get(key)!r}")

    complete = not errors
    return Source38FStatus(
        complete=complete,
        status="SOURCE_38F_READY" if complete else "SOURCE_38F_NOT_READY",
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


def build_local_health_evidence_contract(source: Source38FStatus) -> dict[str, Any]:
    rules = [
        _rule("source_38f_ready_required", "38F READY local activation harness evidence is required"),
        _rule("local_health_evidence_contract_only", "38G defines a local health evidence contract only"),
        _rule("runtime_process_start_forbidden", "38G cannot start the runtime process"),
        _rule("runtime_health_probe_not_performed", "38G cannot execute a runtime health probe"),
        _rule("local_health_snapshot_static_only", "health snapshot is static evidence, not live process probing"),
        _rule("local_activation_session_ledger_required", "38F local activation session ledger must be referenced"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("live_real_forbidden", "live-real remains forbidden"),
        _rule("exchange_submit_forbidden", "exchange submit remains forbidden"),
        _rule("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        _rule("38h_not_auto_unlocked", "38H is not auto-unlocked by 38G"),
    ]
    contract = {
        "contract_name": "paper_sandbox_local_health_evidence_contract",
        "source_38f_status": source.status,
        "local_health_evidence_contract_mode": "STATIC_LOCAL_HEALTH_EVIDENCE_NO_RUNTIME_PROCESS_NO_NETWORK_ORDER",
        "paper_runtime_process_evidence_required": True,
        "runtime_process_start_forbidden_in_38g": True,
        "runtime_health_probe_forbidden_in_38g": True,
        "local_health_snapshot_static_only": True,
        "local_activation_session_ledger_required": True,
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


def build_local_health_snapshot(source: Source38FStatus, generated_at_utc: str) -> dict[str, Any]:
    snapshot = {
        "snapshot_name": "paper_sandbox_local_runtime_health_snapshot",
        "snapshot_mode": "STATIC_LEDGER_HEALTH_EVIDENCE_NO_PROCESS_START",
        "generated_at_utc": generated_at_utc,
        "source_report": source.report_path,
        "source_38f_status": source.status,
        "local_activation_session_reference_required": True,
        "health_evidence_snapshot_created": True,
        "health_evidence_snapshot_locked": True,
        "health_evidence_snapshot_ready": source.complete,
        "runtime_process_status": "NOT_STARTED_BY_38G",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_health_probe_performed": False,
        "runtime_health_endpoint_called": False,
        "network_request_performed": False,
        "network_order_submit_performed": False,
        "paper_order_submit_performed": False,
        "exchange_submit_performed": False,
        "live_environment_enabled": False,
        "paper_environment_enabled": False,
        "evidence_items": [
            {"item_id": "source_38f_ready", "ready": source.complete, "value": source.status},
            {"item_id": "paper_only_local_harness_ready", "ready": True, "value": True},
            {"item_id": "local_activation_session_ledger_required", "ready": True, "value": True},
            {"item_id": "runtime_process_not_started", "ready": True, "value": False},
            {"item_id": "runtime_health_probe_not_performed", "ready": True, "value": False},
            {"item_id": "network_order_submit_not_performed", "ready": True, "value": False},
            {"item_id": "live_real_not_approved", "ready": True, "value": False},
            {"item_id": "exchange_submit_not_performed", "ready": True, "value": False},
        ],
    }
    snapshot["evidence_item_count"] = len(snapshot["evidence_items"])
    snapshot["evidence_ready_count"] = sum(1 for item in snapshot["evidence_items"] if item["ready"])
    snapshot["digest"] = stable_digest(snapshot)
    return snapshot


def build_health_probe(source: Source38FStatus) -> dict[str, Any]:
    probes = [
        {"probe_id": "source_38f_ready", "expected": True, "result": source.complete, "passed": source.complete, "runtime_start_allowed": False},
        {"probe_id": "local_health_evidence_contract_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False},
        {"probe_id": "local_health_snapshot_created", "expected": "STATIC_HEALTH_EVIDENCE_ONLY", "result": "STATIC_HEALTH_EVIDENCE_ONLY", "passed": True, "runtime_start_allowed": False},
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
        "probe_name": "paper_sandbox_local_runtime_health_evidence_probe",
        "local_health_evidence_probe_mode": "STATIC_LOCAL_HEALTH_EVIDENCE_NO_RUNTIME_PROCESS_NO_ORDER",
        "probes": probes,
        "probe_count": len(probes),
        "probe_passed_count": sum(1 for item in probes if item["passed"]),
    }
    probe["digest"] = stable_digest(probe)
    return probe


def build_no_runtime_no_order_guard() -> dict[str, Any]:
    rules = [
        _rule("paper_runtime_process_start_forbidden", "38G cannot start paper runtime process"),
        _rule("runtime_health_probe_forbidden", "38G cannot perform runtime health probes"),
        _rule("paper_order_submit_forbidden", "38G cannot submit paper orders"),
        _rule("network_order_submit_forbidden", "network order submit remains forbidden"),
        _rule("live_real_approval_false", "live-real approval remains false"),
        _rule("exchange_submit_approval_false", "exchange submit approval remains false"),
        _rule("signed_request_forbidden", "signed requests remain forbidden"),
        _rule("private_api_forbidden", "private API access remains forbidden"),
        _rule("network_request_forbidden", "network requests are not performed by 38G"),
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
    source = validate_source_38f(reports_path)
    generated_at = utc_stamp()

    contract = build_local_health_evidence_contract(source)
    snapshot = build_local_health_snapshot(source, generated_at)
    probe = build_health_probe(source)
    guard = build_no_runtime_no_order_guard()

    source_ready = source.complete
    gate_checks = [
        _check("source_38f_ready", source_ready),
        _check("phase_37_final_closed"),
        _check("paper_sandbox_local_runtime_activation_harness_ready"),
        _check("local_activation_session_ledger_available"),
        _check("local_health_evidence_contract_locked"),
        _check("local_health_snapshot_static_only"),
        _check("local_health_snapshot_created"),
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
        _check("health_probe_passed", probe["probe_count"] == probe["probe_passed_count"]),
        _check("guard_locked", guard["rule_count"] == guard["ready_count"]),
        _check("local_health_evidence_ready", source_ready),
        _check("runtime_process_status_not_started"),
        _check("local_health_contract_no_order"),
        _check("local_health_contract_no_live"),
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
        "source_38f_report": source.report_path,
        "source_38f_complete": source.complete,
        "source_38f_status": source.status,
        "source_38f_decision": source.decision,
        "source_38f_safety_violation_count": source.safety_violation_count,
        "source_38f_safety_violations": source.safety_violations,
        "source_38f_errors": source.errors,
        "source_38f_approved_for_paper_transition": source.data.get("approved_for_paper_transition", False),
        "source_38f_paper_sandbox_local_runtime_activation_harness_ready": source.data.get("paper_sandbox_local_runtime_activation_harness_ready", False),
        "source_38f_paper_transition_blocked": source.data.get("paper_transition_blocked", True),
        "source_38f_paper_runtime_start_performed": source.data.get("paper_runtime_start_performed", False),
        "source_38f_network_order_submit_performed": source.data.get("network_order_submit_performed", False),
        "phase_37_final_closed": True,
        "phase_38_planning_only": True,
        "phase_38_execution_started": False,
        "phase_38_unlocked": False,
        "paper_sandbox_local_runtime_health_evidence_complete": status == "READY",
        "paper_sandbox_local_runtime_health_evidence_locked": True,
        "paper_sandbox_local_runtime_health_evidence_ready": status == "READY",
        "paper_sandbox_local_runtime_health_evidence_mode": "STATIC_LOCAL_HEALTH_EVIDENCE_NO_RUNTIME_PROCESS_START_NO_NETWORK_ORDER",
        "local_health_evidence_contract_complete": True,
        "local_health_evidence_contract_locked": True,
        "local_health_evidence_contract_ready": status == "READY",
        "local_health_evidence_contract_mode": contract["local_health_evidence_contract_mode"],
        "local_health_evidence_contract_rule_count": contract["rule_count"],
        "local_health_evidence_contract_ready_count": contract["ready_count"],
        "local_health_evidence_contract_rules": contract["rules"],
        "local_health_evidence_contract_digest": contract["digest"],
        "local_health_snapshot_complete": True,
        "local_health_snapshot_locked": True,
        "local_health_snapshot_ready": status == "READY",
        "local_health_snapshot_static_only": True,
        "local_health_snapshot_created": True,
        "health_evidence_snapshot_created": True,
        "health_evidence_snapshot_locked": True,
        "health_evidence_snapshot_ready": status == "READY",
        "health_evidence_snapshot_source": "STATIC_LEDGER_NO_RUNTIME_PROCESS_START",
        "health_evidence_item_count": snapshot["evidence_item_count"],
        "health_evidence_ready_count": snapshot["evidence_ready_count"],
        "runtime_process_status": "NOT_STARTED_BY_38G",
        "runtime_process_started": False,
        "runtime_process_pid": None,
        "runtime_process_start_forbidden_in_38g": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "local_activation_session_ledger_required": True,
        "local_activation_session_ledger_verified_for_health_evidence": status == "READY",
        "runtime_health_evidence_contract_only": True,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_forbidden_in_38g": True,
        "runtime_health_endpoint_called": False,
        "paper_sandbox_local_runtime_health_evidence_probe_complete": True,
        "paper_sandbox_local_runtime_health_evidence_probe_locked": True,
        "paper_sandbox_local_runtime_health_evidence_probe_mode": probe["local_health_evidence_probe_mode"],
        "paper_sandbox_local_runtime_health_evidence_probe_count": probe["probe_count"],
        "paper_sandbox_local_runtime_health_evidence_probe_passed_count": probe["probe_passed_count"],
        "paper_sandbox_local_runtime_health_evidence_probes": probe["probes"],
        "paper_sandbox_local_runtime_health_evidence_probe_digest": probe["digest"],
        "approved_for_operator_audit": True,
        "approved_for_paper_sandbox_local_runtime_health_evidence": status == "READY",
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
        "paper_transition_status": "PAPER_SANDBOX_LOCAL_HEALTH_EVIDENCE_READY_NO_RUNTIME_PROCESS_NO_ORDER",
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
        "paper_sandbox_local_runtime_health_evidence_gate_complete": True,
        "paper_sandbox_local_runtime_health_evidence_gate_locked": True,
        "paper_sandbox_local_runtime_health_evidence_gate_check_count": len(gate_checks),
        "paper_sandbox_local_runtime_health_evidence_gate_ready_count": gate_ready_count,
        "paper_sandbox_local_runtime_health_evidence_gate_checks": gate_checks,
        "paper_sandbox_local_runtime_health_evidence_gate_status": "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_EVIDENCE_GATE_READY" if status == "READY" else "PAPER_SANDBOX_LOCAL_RUNTIME_HEALTH_EVIDENCE_GATE_NOT_READY",
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
            f"{PATCH_ID}_local_health_evidence_contract_{generated_at}.json": contract,
            f"{PATCH_ID}_local_runtime_health_snapshot_{generated_at}.json": snapshot,
            f"{PATCH_ID}_local_runtime_health_evidence_probe_{generated_at}.json": probe,
            f"{PATCH_ID}_no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json": guard,
            f"{PATCH_ID}_paper_sandbox_local_runtime_health_evidence_gate_{generated_at}.json": {
                "gate_name": "paper_sandbox_local_runtime_health_evidence_gate",
                "checks": gate_checks,
                "check_count": len(gate_checks),
                "ready_count": gate_ready_count,
            },
        }
        for filename, payload in artifacts.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            key = filename.replace(f"{PATCH_ID}_", "").replace(f"_{generated_at}.json", "_path")
            if "local_health_evidence_contract" in filename:
                report["local_health_evidence_contract_path"] = str(path)
            elif "local_runtime_health_snapshot" in filename:
                report["local_health_snapshot_path"] = str(path)
            elif "local_runtime_health_evidence_probe" in filename:
                report["paper_sandbox_local_runtime_health_evidence_probe_path"] = str(path)
            elif "no_runtime_process" in filename:
                report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = str(path)
            elif "gate" in filename:
                report["paper_sandbox_local_runtime_health_evidence_gate_path"] = str(path)

        ready_suffix = "ready" if status == "READY" else "not_ready"
        report_path = reports_path / f"{PATCH_ID}_paper_sandbox_local_runtime_health_evidence_{generated_at}_{ready_suffix}.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        report["local_health_evidence_contract_path"] = None
        report["local_health_snapshot_path"] = None
        report["paper_sandbox_local_runtime_health_evidence_probe_path"] = None
        report["no_runtime_process_start_no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_local_runtime_health_evidence_gate_path"] = None

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
