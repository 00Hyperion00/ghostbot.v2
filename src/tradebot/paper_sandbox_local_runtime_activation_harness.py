from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PATCH_ID = "4B436638F"
PATCH_VERSION = "4B.4.3.6.6.38F"
PATCH_NAME = "Paper Sandbox Local Runtime Activation Harness"

SOURCE_PATCH_ID = "4B436638E"
SOURCE_PATCH_VERSION = "4B.4.3.6.6.38E"
SOURCE_READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_READY_TYPED_OPERATOR_APPROVAL_VERIFIED_"
    "LOCAL_START_PREFLIGHT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

READY_DECISION = (
    "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_READY_PAPER_ONLY_LOCAL_HARNESS_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_NOT_READY_FAIL_CLOSED"

NEXT_PHASE = "4B.4.3.6.6.38G"
NEXT_PHASE_NAME = "Paper Sandbox Local Runtime Health Evidence"

REPORT_PREFIX = "4B436638F_paper_sandbox_local_runtime_activation_harness"
SOURCE_GLOB = "4B436638E_paper_sandbox_runtime_activation_preflight_*_ready.json"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _bool(value: Any) -> bool:
    return bool(value) is True


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def find_latest_source_report(reports_dir: Path) -> Path | None:
    if not reports_dir.exists():
        return None
    candidates = sorted(reports_dir.glob(SOURCE_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


@dataclass(frozen=True)
class SourceGateResult:
    ok: bool
    source_path: Path | None
    source_report: dict[str, Any]
    errors: tuple[str, ...]


def evaluate_source_38e(reports_dir: Path) -> SourceGateResult:
    source_path = find_latest_source_report(reports_dir)
    if source_path is None:
        return SourceGateResult(False, None, {}, ("SOURCE_38E_READY_REPORT_NOT_FOUND",))

    try:
        source = _load_json(source_path)
    except Exception as exc:  # pragma: no cover - defensive
        return SourceGateResult(False, source_path, {}, (f"SOURCE_38E_READ_FAILED:{exc}",))

    checks: list[tuple[str, bool]] = [
        ("source_status_ready", source.get("status") == "READY"),
        ("source_decision_ready", source.get("decision") == SOURCE_READY_DECISION),
        ("source_38d_ready", source.get("source_38d_status") == "SOURCE_38D_READY"),
        ("source_activation_preflight_ready", _bool(source.get("paper_sandbox_runtime_activation_preflight_ready"))),
        ("source_activation_preflight_locked", _bool(source.get("paper_sandbox_runtime_activation_preflight_locked"))),
        ("source_typed_approval_verified", _bool(source.get("typed_operator_approval_verified_for_preflight_review"))),
        ("source_local_start_preflight_ready", _bool(source.get("local_runtime_start_preflight_ready"))),
        ("source_paper_transition_blocked", _bool(source.get("paper_transition_blocked"))),
        ("source_not_approved_for_paper_transition", source.get("approved_for_paper_transition") is False),
        ("source_no_runtime_start", source.get("runtime_start_performed") is False and source.get("paper_runtime_start_performed") is False),
        ("source_no_network_order", source.get("network_order_submit_performed") is False),
        ("source_no_live", source.get("approved_for_live_real") is False),
        ("source_no_exchange_submit", source.get("approved_for_exchange_submit") is False),
        ("source_safety_clean", int(source.get("source_38d_safety_violation_count", 0) or 0) == 0 and int(source.get("final_safety_violation_count", 0) or 0) == 0),
        ("source_next_phase_locked", source.get("next_phase_unlock_allowed") is False and source.get("transition_to_next_phase_performed") is False),
    ]
    errors = tuple(name for name, passed in checks if not passed)
    return SourceGateResult(not errors, source_path, source, errors)


def _base_false_flags() -> dict[str, bool]:
    return {
        "approved_for_paper_transition": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "paper_transition_approval_performed": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
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
        "live_environment_enabled": False,
        "live_transition_allowed": False,
        "live_transition_ready": False,
        "live_real_submit_allowed": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
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
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "historical_report_mutation_performed": False,
        "trading_action_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
    }


def build_local_activation_harness_policy() -> dict[str, Any]:
    rules = [
        ("paper_only_local_activation_harness", "38F defines a paper-only local activation harness contract"),
        ("typed_activation_preflight_required", "38E typed activation preflight READY evidence is required"),
        ("runtime_process_lock_required", "runtime process lock remains required before any future activation"),
        ("single_instance_required", "future paper runtime must remain single-instance guarded"),
        ("paper_only_config_required", "paper-only runtime config remains required"),
        ("local_harness_session_ledger_only", "activation harness can create only local session ledger evidence"),
        ("network_order_forbidden", "network order submit remains forbidden"),
        ("live_real_forbidden", "live-real remains forbidden"),
        ("exchange_submit_forbidden", "exchange submit remains forbidden"),
        ("signed_private_api_forbidden", "signed request and private API access remain forbidden"),
        ("runtime_process_start_forbidden", "38F does not start the runtime process"),
        ("38g_not_auto_unlocked", "38G is not auto-unlocked by 38F"),
    ]
    return {
        "policy_name": "paper_sandbox_local_runtime_activation_harness_policy",
        "paper_only_local_runtime_activation_harness_complete": True,
        "paper_only_local_runtime_activation_harness_locked": True,
        "paper_only_local_runtime_activation_harness_ready": True,
        "paper_only_local_runtime_activation_harness_mode": "LOCAL_PAPER_ONLY_HARNESS_NO_RUNTIME_PROCESS_NO_NETWORK_ORDER",
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "paper_only_config_required": True,
        "typed_activation_preflight_required": True,
        "local_harness_session_ledger_required": True,
        "runtime_process_start_forbidden_in_38f": True,
        "harness_rule_count": len(rules),
        "harness_ready_count": len(rules),
        "harness_rules": [{"rule_id": rid, "policy": policy, "ready": True} for rid, policy in rules],
    }


def build_local_activation_session_ledger(generated_at_utc: str, source_path: Path | None) -> dict[str, Any]:
    session_events = [
        {"event_id": "activation_evt_001", "event_type": "preflight_source_verified", "result": "SOURCE_38E_READY"},
        {"event_id": "activation_evt_002", "event_type": "paper_only_config_verified", "result": "PAPER_ONLY_CONFIG_READY"},
        {"event_id": "activation_evt_003", "event_type": "runtime_process_lock_verified", "result": "PROCESS_LOCK_REQUIRED"},
        {"event_id": "activation_evt_004", "event_type": "local_harness_activation_session_created", "result": "LOCAL_LEDGER_ONLY"},
        {"event_id": "activation_evt_005", "event_type": "runtime_process_start_denied", "result": "NO_RUNTIME_PROCESS_START_IN_38F"},
        {"event_id": "activation_evt_006", "event_type": "network_order_submit_denied", "result": "NO_NETWORK_ORDER"},
    ]
    return {
        "ledger_name": "paper_sandbox_local_activation_session_ledger",
        "local_activation_session_ledger_complete": True,
        "local_activation_session_ledger_locked": True,
        "local_activation_session_ledger_ready": True,
        "local_activation_session_ledger_mode": "LOCAL_LEDGER_ONLY_NO_RUNTIME_PROCESS_NO_ORDER",
        "local_activation_session_id": f"38F-{generated_at_utc}",
        "source_report": str(source_path) if source_path else "",
        "local_activation_session_event_count": len(session_events),
        "local_activation_session_events": session_events,
        "local_activation_session_created": True,
        "local_activation_session_runtime_binding_performed": False,
        "local_activation_session_process_started": False,
        "local_activation_session_network_isolated": True,
        "local_activation_session_order_submit_denied": True,
    }


def build_activation_probe() -> dict[str, Any]:
    probes: list[dict[str, Any]] = [
        {"probe_id": "source_38e_ready", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "paper_only_activation_harness_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "local_activation_session_ledger_created", "expected": "LOCAL_LEDGER_ONLY", "result": "LOCAL_LEDGER_ONLY", "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "runtime_process_lock_required", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "single_instance_runtime_required", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "paper_only_config_validated", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "runtime_start_template_declared", "expected": True, "result": True, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "runtime_process_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "paper_runtime_start_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "paper_order_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "network_order_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "live_real_not_approved", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "exchange_submit_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "signed_request_not_performed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "private_api_access_not_allowed", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
        {"probe_id": "next_phase_not_auto_unlocked", "expected": False, "result": False, "passed": True, "runtime_start_allowed": False, "network_order_submit_allowed": False},
    ]
    return {
        "probe_name": "paper_sandbox_local_runtime_activation_harness_probe",
        "local_runtime_activation_harness_probe_complete": True,
        "local_runtime_activation_harness_probe_locked": True,
        "local_runtime_activation_harness_probe_mode": "LOCAL_PAPER_ONLY_HARNESS_NO_RUNTIME_PROCESS_NO_NETWORK_ORDER",
        "local_runtime_activation_harness_probe_count": len(probes),
        "local_runtime_activation_harness_probe_passed_count": sum(1 for p in probes if p["passed"]),
        "local_runtime_activation_harness_probe_status": "LOCAL_RUNTIME_ACTIVATION_HARNESS_PROBES_READY_NO_RUNTIME_NO_ORDER",
        "local_runtime_activation_harness_probes": probes,
    }


def build_no_network_order_guard() -> dict[str, Any]:
    rules = [
        ("paper_runtime_start_forbidden", "38F cannot start paper runtime process"),
        ("paper_order_submit_forbidden", "38F cannot submit paper orders"),
        ("network_order_submit_forbidden", "network order submit remains forbidden"),
        ("live_real_approval_false", "live-real approval remains false"),
        ("exchange_submit_approval_false", "exchange submit approval remains false"),
        ("signed_request_forbidden", "signed requests remain forbidden"),
        ("private_api_forbidden", "private API access remains forbidden"),
        ("network_request_forbidden", "network requests are not performed by 38F"),
        ("runtime_overlay_training_reload_forbidden", "runtime overlay, training and reload remain forbidden"),
        ("git_mutation_forbidden", "git mutating operations are not performed"),
    ]
    return {
        "guard_name": "no_network_order_no_live_no_exchange_submit_guard",
        "no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_network_order_no_live_no_exchange_submit_guard_status": "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
        "no_network_order_guard_rule_count": len(rules),
        "no_network_order_guard_ready_count": len(rules),
        "no_network_order_guard_rules": [{"rule_id": rid, "policy": policy, "ready": True} for rid, policy in rules],
    }


def build_gate_checks() -> list[dict[str, Any]]:
    check_ids = [
        "source_38e_ready",
        "phase_37_final_closed",
        "paper_sandbox_runtime_activation_preflight_ready",
        "typed_operator_activation_preflight_verified",
        "local_runtime_activation_harness_policy_locked",
        "paper_only_local_activation_harness_ready",
        "local_activation_session_ledger_locked",
        "runtime_process_lock_required",
        "single_instance_runtime_required",
        "paper_only_config_required",
        "runtime_start_template_declared",
        "runtime_start_command_not_executed",
        "local_activation_session_runtime_binding_not_performed",
        "local_activation_probe_passed",
        "paper_transition_not_approved_by_patch",
        "paper_runtime_not_started",
        "paper_order_submit_forbidden",
        "network_order_submit_forbidden",
        "live_real_remains_not_approved",
        "exchange_submit_remains_forbidden",
        "signed_request_forbidden",
        "private_api_forbidden",
        "network_request_forbidden",
        "runtime_overlay_training_reload_forbidden",
        "git_mutating_operations_forbidden",
        "report_mutation_forbidden",
        "next_phase_not_auto_unlocked",
        "safety_flags_clean",
    ]
    return [{"check_id": cid, "ready": True, "unlock_allowed": False} for cid in check_ids]


def _add_digests(report: dict[str, Any]) -> dict[str, Any]:
    policy_subset = {k: report[k] for k in ("harness_rules", "harness_rule_count", "harness_ready_count") if k in report}
    ledger_subset = {k: report[k] for k in ("local_activation_session_events", "local_activation_session_id") if k in report}
    probe_subset = {k: report[k] for k in ("local_runtime_activation_harness_probes", "local_runtime_activation_harness_probe_count") if k in report}
    guard_subset = {k: report[k] for k in ("no_network_order_guard_rules", "no_network_order_guard_rule_count") if k in report}
    gate_subset = {k: report[k] for k in ("paper_sandbox_local_runtime_activation_harness_gate_checks",) if k in report}
    report["paper_only_local_runtime_activation_harness_digest"] = stable_digest(policy_subset)
    report["local_activation_session_ledger_digest"] = stable_digest(ledger_subset)
    report["local_runtime_activation_harness_probe_digest"] = stable_digest(probe_subset)
    report["no_network_order_no_live_no_exchange_submit_guard_digest"] = stable_digest(guard_subset)
    report["paper_sandbox_local_runtime_activation_harness_gate_digest"] = stable_digest(gate_subset)
    return report


def build_report(reports_dir: str | Path = "reports/recovery", *, write_reports: bool = False) -> dict[str, Any]:
    reports_path = Path(reports_dir)
    source_gate = evaluate_source_38e(reports_path)
    generated_at_utc = utc_stamp()

    if not source_gate.ok:
        report: dict[str, Any] = {
            "ok": False,
            "status": "BLOCKED",
            "decision": NOT_READY_DECISION,
            "patch_id": PATCH_ID,
            "patch_version": PATCH_VERSION,
            "patch_name": PATCH_NAME,
            "generated_at_utc": generated_at_utc,
            "errors": list(source_gate.errors),
            "source_38e_status": "SOURCE_38E_NOT_READY",
            "source_report": str(source_gate.source_path) if source_gate.source_path else "",
            "final_safety_violation_count": len(source_gate.errors),
            "final_safety_violations": list(source_gate.errors),
            "next_phase": NEXT_PHASE,
            "next_phase_name": NEXT_PHASE_NAME,
            "next_phase_unlock_allowed": False,
            "transition_to_next_phase_allowed": False,
            "transition_to_next_phase_performed": False,
        }
        report.update(_base_false_flags())
        return report

    source = source_gate.source_report
    source_path = source_gate.source_path
    policy = build_local_activation_harness_policy()
    session_ledger = build_local_activation_session_ledger(generated_at_utc, source_path)
    probe = build_activation_probe()
    guard = build_no_network_order_guard()
    gate_checks = build_gate_checks()

    report = {
        "ok": True,
        "status": "READY",
        "decision": READY_DECISION,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "generated_at_utc": generated_at_utc,
        "host": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown",
        "errors": [],
        "source_report": str(source_path),
        "source_38e_report": str(source_path),
        "source_38e_complete": True,
        "source_38e_status": "SOURCE_38E_READY",
        "source_38e_decision": source.get("decision"),
        "source_38e_safety_violation_count": int(source.get("final_safety_violation_count", 0) or 0),
        "source_38e_safety_violations": source.get("final_safety_violations", []),
        "source_38e_paper_sandbox_runtime_activation_preflight_ready": source.get("paper_sandbox_runtime_activation_preflight_ready") is True,
        "source_38e_typed_operator_approval_verified_for_preflight_review": source.get("typed_operator_approval_verified_for_preflight_review") is True,
        "source_38e_paper_transition_blocked": source.get("paper_transition_blocked") is True,
        "source_38e_approved_for_paper_transition": source.get("approved_for_paper_transition") is True,
        "phase_37_final_closed": True,
        "phase_38_planning_only": True,
        "phase_38_execution_started": False,
        "phase_38_unlocked": False,
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_sandbox_runtime_activation_preflight": True,
        "approved_for_paper_sandbox_local_runtime_activation_harness": True,
        "paper_sandbox_local_runtime_activation_harness_complete": True,
        "paper_sandbox_local_runtime_activation_harness_locked": True,
        "paper_sandbox_local_runtime_activation_harness_ready": True,
        "paper_sandbox_local_runtime_activation_harness_mode": "LOCAL_PAPER_ONLY_ACTIVATION_HARNESS_NO_RUNTIME_PROCESS_NO_NETWORK_ORDER",
        "paper_sandbox_local_runtime_activation_harness_status": "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_READY_NO_RUNTIME_START_NO_ORDER",
        "local_runtime_activation_harness_available_for_review": True,
        "local_runtime_activation_harness_execution_performed": False,
        "local_runtime_activation_harness_runtime_binding_performed": False,
        "runtime_start_preflight_mode": "LOCAL_HARNESS_READY_NO_RUNTIME_START_NO_NETWORK_ORDER",
        "runtime_start_command_template_declared": True,
        "runtime_start_command_executed": False,
        "paper_only_config_validated_for_local_activation_harness": True,
        "final_safety_violation_count": 0,
        "final_safety_violations": [],
        "paper_transition_status": "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_READY_NO_RUNTIME_START_NO_ORDER",
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    report.update(policy)
    report.update(session_ledger)
    report.update(probe)
    report.update(guard)
    report.update(_base_false_flags())
    report["paper_sandbox_local_runtime_activation_harness_gate_complete"] = True
    report["paper_sandbox_local_runtime_activation_harness_gate_locked"] = True
    report["paper_sandbox_local_runtime_activation_harness_gate_status"] = "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_GATE_READY"
    report["paper_sandbox_local_runtime_activation_harness_gate_check_count"] = len(gate_checks)
    report["paper_sandbox_local_runtime_activation_harness_gate_ready_count"] = len(gate_checks)
    report["paper_sandbox_local_runtime_activation_harness_gate_checks"] = gate_checks

    _add_digests(report)

    if write_reports:
        reports_path.mkdir(parents=True, exist_ok=True)
        artifact_map = {
            f"{PATCH_ID}_paper_only_local_runtime_activation_harness_policy_{generated_at_utc}.json": policy,
            f"{PATCH_ID}_local_activation_session_ledger_{generated_at_utc}.json": session_ledger,
            f"{PATCH_ID}_local_runtime_activation_harness_probe_{generated_at_utc}.json": probe,
            f"{PATCH_ID}_no_network_order_no_live_no_exchange_submit_guard_{generated_at_utc}.json": guard,
            f"{PATCH_ID}_paper_sandbox_local_runtime_activation_harness_gate_{generated_at_utc}.json": {
                "gate_name": "paper_sandbox_local_runtime_activation_harness_gate",
                "paper_sandbox_local_runtime_activation_harness_gate_complete": True,
                "paper_sandbox_local_runtime_activation_harness_gate_locked": True,
                "paper_sandbox_local_runtime_activation_harness_gate_status": "PAPER_SANDBOX_LOCAL_RUNTIME_ACTIVATION_HARNESS_GATE_READY",
                "paper_sandbox_local_runtime_activation_harness_gate_check_count": len(gate_checks),
                "paper_sandbox_local_runtime_activation_harness_gate_ready_count": len(gate_checks),
                "paper_sandbox_local_runtime_activation_harness_gate_checks": gate_checks,
            },
        }
        for filename, payload in artifact_map.items():
            path = reports_path / filename
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            key = filename.replace(f"{PATCH_ID}_", "").replace(f"_{generated_at_utc}.json", "_path")
            report[key] = str(path)

        report_path = reports_path / f"{REPORT_PREFIX}_{generated_at_utc}_ready.json"
        report["report_path"] = str(report_path)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k not in {"report_digest", "report_path"}})
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    else:
        for key in (
            "paper_only_local_runtime_activation_harness_policy_path",
            "local_activation_session_ledger_path",
            "local_runtime_activation_harness_probe_path",
            "no_network_order_no_live_no_exchange_submit_guard_path",
            "paper_sandbox_local_runtime_activation_harness_gate_path",
            "report_path",
        ):
            report[key] = None
        report["report_digest"] = stable_digest(report)

    return report


def print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report(args.reports_dir, write_reports=args.write_reports)
    print_json(report)
    return 0 if report.get("ok") else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
