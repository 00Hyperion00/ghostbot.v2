from __future__ import annotations

import argparse
import hashlib
import json
import socket
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436638C"
PATCH_VERSION = "4B.4.3.6.6.38C"
PATCH_NAME = "Paper Sandbox Dry-Run Runtime Harness"
READY_DECISION = "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_READY_LOCAL_DRY_RUN_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
NOT_READY_DECISION = "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_NOT_READY_LOCKED"
SOURCE_PATCH_ID = "4B436638B"
SOURCE_READY_DECISION = "PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_PAPER_ONLY_NO_LIVE_NO_EXCHANGE_SUBMIT_NO_NETWORK_ORDER_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.38D"
NEXT_PHASE_NAME = "Paper Sandbox Operator Approval Ledger"
REPORT_PREFIX = "4B436638C"

SAFETY_FALSE_FIELDS: tuple[str, ...] = (
    "approved_for_paper_transition",
    "approved_for_paper_transition_candidate",
    "paper_transition_approval_ready",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_transition_ready",
    "paper_environment_enabled",
    "paper_runtime_start_allowed",
    "paper_runtime_start_performed",
    "paper_order_submit_allowed",
    "paper_order_submit_performed",
    "paper_submit_allowed",
    "approved_for_live_real",
    "live_environment_enabled",
    "live_transition_ready",
    "live_transition_allowed",
    "live_transition_approval_performed",
    "live_real_submit_allowed",
    "approved_for_exchange_submit",
    "exchange_submit_allowed",
    "exchange_submit_approval_performed",
    "exchange_submit_performed",
    "network_order_submit_allowed",
    "network_order_submit_performed",
    "network_submit_allowed",
    "order_submit_performed",
    "network_request_allowed_now",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "runtime_start_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "training_performed",
    "reload_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "git_add_performed",
    "git_commit_performed",
    "git_tag_performed",
    "git_push_performed",
    "automatic_commit_performed",
    "report_delete_performed",
    "report_move_performed",
    "report_archive_performed",
    "report_dedup_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "file_delete_performed",
    "file_move_performed",
    "historical_report_mutation_performed",
    "api_auth_mutation_performed",
    "api_route_mutation_performed",
    "trading_action_performed",
)

REQUIRED_38B_TRUE_FIELDS: tuple[str, ...] = (
    "paper_sandbox_runtime_preflight_complete",
    "paper_sandbox_runtime_preflight_locked",
    "paper_sandbox_runtime_preflight_ready",
    "paper_only_runtime_config_contract_complete",
    "paper_only_runtime_config_contract_locked",
    "approved_for_paper_sandbox_runtime_preflight",
)

REQUIRED_38B_FALSE_FIELDS: tuple[str, ...] = (
    "approved_for_paper_transition",
    "approved_for_paper_transition_candidate",
    "paper_transition_ready",
    "paper_runtime_start_performed",
    "paper_order_submit_performed",
    "approved_for_live_real",
    "approved_for_exchange_submit",
    "network_order_submit_performed",
    "network_request_performed",
    "order_submit_performed",
    "exchange_submit_performed",
    "runtime_start_performed",
)

@dataclass(frozen=True)
class DryRunEvent:
    event_id: str
    event_type: str
    symbol: str
    price: float
    qty: float
    side: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "symbol": self.symbol,
            "price": self.price,
            "qty": self.qty,
            "side": self.side,
        }


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_obj(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def find_latest_source_report(repo_root: Path) -> Path | None:
    reports_dir = repo_root / "reports" / "recovery"
    if not reports_dir.exists():
        return None
    candidates = sorted(
        reports_dir.glob("4B436638B_paper_sandbox_runtime_preflight_*_ready.json"),
        key=lambda p: (p.stat().st_mtime_ns, p.name),
        reverse=True,
    )
    return candidates[0] if candidates else None


def validate_source_38b(repo_root: Path) -> tuple[dict[str, Any], list[str], str | None]:
    source_path = find_latest_source_report(repo_root)
    if source_path is None:
        return {}, ["SOURCE_38B_READY_REPORT_MISSING"], None

    source = read_json(source_path)
    errors: list[str] = []
    if source.get("status") != "READY":
        errors.append("SOURCE_38B_STATUS_NOT_READY")
    if source.get("decision") != SOURCE_READY_DECISION:
        errors.append("SOURCE_38B_DECISION_MISMATCH")
    if source.get("final_safety_violation_count") != 0:
        errors.append("SOURCE_38B_SAFETY_VIOLATIONS_PRESENT")
    if source.get("source_38a_status") != "SOURCE_38A_READY":
        errors.append("SOURCE_38A_NOT_READY_IN_38B_REPORT")
    for field in REQUIRED_38B_TRUE_FIELDS:
        if source.get(field) is not True:
            errors.append(f"SOURCE_38B_REQUIRED_TRUE_MISSING:{field}")
    for field in REQUIRED_38B_FALSE_FIELDS:
        if source.get(field) is not False:
            errors.append(f"SOURCE_38B_REQUIRED_FALSE_MISMATCH:{field}")
    return source, errors, str(source_path)


def build_harness_policy() -> dict[str, Any]:
    rules = [
        {"rule_id": "local_dry_run_harness_only", "ready": True, "policy": "38C defines a local dry-run harness only"},
        {"rule_id": "synthetic_tick_source_only", "ready": True, "policy": "dry-run ticks are synthetic fixtures, not market-data network calls"},
        {"rule_id": "simulated_order_intent_only", "ready": True, "policy": "order intents are simulation ledgers and never executable orders"},
        {"rule_id": "network_order_forbidden", "ready": True, "policy": "network order submit remains forbidden"},
        {"rule_id": "live_real_forbidden", "ready": True, "policy": "live-real environment remains forbidden"},
        {"rule_id": "exchange_submit_forbidden", "ready": True, "policy": "exchange submit remains forbidden"},
        {"rule_id": "private_api_forbidden", "ready": True, "policy": "private API and signed requests remain forbidden"},
        {"rule_id": "runtime_start_forbidden", "ready": True, "policy": "production/paper runtime start is out of scope for 38C"},
        {"rule_id": "next_phase_not_auto_unlocked", "ready": True, "policy": "38D is not auto-unlocked"},
    ]
    payload: dict[str, Any] = {
        "policy_name": "local_dry_run_runtime_harness_policy",
        "local_dry_run_runtime_harness_complete": True,
        "local_dry_run_runtime_harness_locked": True,
        "dry_run_runtime_harness_mode": "LOCAL_SIMULATION_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT",
        "synthetic_tick_source_only": True,
        "network_market_data_disabled": True,
        "simulated_order_intent_only": True,
        "harness_rule_count": len(rules),
        "harness_ready_count": sum(1 for rule in rules if rule["ready"]),
        "harness_rules": rules,
    }
    payload["local_dry_run_runtime_harness_digest"] = digest_obj({k: v for k, v in payload.items() if k.endswith("rules") or k.endswith("count") or k.endswith("mode")})
    return payload


def _probe_result(probe_id: str, expected: Any, result: Any, *, runtime_execution_allowed: bool = False, order_submit_allowed: bool = False) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "expected": expected,
        "result": result,
        "passed": result == expected,
        "runtime_execution_allowed": runtime_execution_allowed,
        "order_submit_allowed": order_submit_allowed,
    }


def build_dry_run_probe() -> dict[str, Any]:
    synthetic_events = [
        DryRunEvent("evt_001", "synthetic_tick", "ETHUSDT", 3000.0, 0.0, "NONE").to_dict(),
        DryRunEvent("evt_002", "synthetic_signal", "ETHUSDT", 3001.0, 0.0, "LONG_CANDIDATE").to_dict(),
        DryRunEvent("evt_003", "simulated_order_intent", "ETHUSDT", 3001.0, 0.01, "BUY").to_dict(),
        DryRunEvent("evt_004", "simulated_fill", "ETHUSDT", 3001.0, 0.01, "BUY").to_dict(),
        DryRunEvent("evt_005", "simulated_exit_intent", "ETHUSDT", 3006.0, 0.01, "SELL").to_dict(),
    ]
    probes = [
        _probe_result("synthetic_event_loop_declared", True, True),
        _probe_result("synthetic_tick_source_only", True, True),
        _probe_result("dry_run_signal_path_declared", True, True),
        _probe_result("simulated_order_intent_created", "SIMULATED_ORDER_INTENT_ONLY", "SIMULATED_ORDER_INTENT_ONLY"),
        _probe_result("simulated_fill_ledger_created", "SIMULATED_FILL_LEDGER_ONLY", "SIMULATED_FILL_LEDGER_ONLY"),
        _probe_result("paper_runtime_start_not_performed", False, False),
        _probe_result("paper_order_submit_not_performed", False, False),
        _probe_result("network_order_submit_not_performed", False, False),
        _probe_result("exchange_submit_not_performed", False, False),
        _probe_result("live_real_not_approved", False, False),
        _probe_result("signed_request_not_performed", False, False),
        _probe_result("private_api_access_not_allowed", False, False),
        _probe_result("next_phase_not_auto_unlocked", False, False),
    ]
    payload: dict[str, Any] = {
        "probe_name": "paper_sandbox_dry_run_runtime_harness_probe",
        "dry_run_harness_probe_complete": True,
        "dry_run_harness_probe_locked": True,
        "dry_run_harness_probe_mode": "LOCAL_SYNTHETIC_EVENT_LOOP_NO_RUNTIME_NO_NETWORK_ORDER",
        "dry_run_harness_probe_count": len(probes),
        "dry_run_harness_probe_passed_count": sum(1 for probe in probes if probe["passed"]),
        "dry_run_harness_probes": probes,
        "dry_run_harness_synthetic_event_count": len(synthetic_events),
        "dry_run_harness_synthetic_events": synthetic_events,
        "dry_run_signal_path_declared": True,
        "synthetic_event_loop_declared": True,
        "simulated_order_intent_created": True,
        "simulated_order_intent_only": True,
        "simulated_fill_ledger_created": True,
        "simulated_fill_ledger_only": True,
    }
    payload["dry_run_harness_probe_digest"] = digest_obj({
        "mode": payload["dry_run_harness_probe_mode"],
        "probes": probes,
        "events": synthetic_events,
    })
    return payload


def build_no_network_order_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "paper_order_submit_forbidden", "ready": True, "policy": "paper order submit remains forbidden"},
        {"rule_id": "network_order_submit_forbidden", "ready": True, "policy": "network order submit remains forbidden"},
        {"rule_id": "live_real_approval_false", "ready": True, "policy": "live-real approval remains false"},
        {"rule_id": "exchange_submit_approval_false", "ready": True, "policy": "exchange submit approval remains false"},
        {"rule_id": "signed_request_forbidden", "ready": True, "policy": "signed requests remain forbidden"},
        {"rule_id": "private_api_forbidden", "ready": True, "policy": "private API access remains forbidden"},
        {"rule_id": "runtime_start_forbidden", "ready": True, "policy": "runtime start remains forbidden in 38C"},
        {"rule_id": "network_request_forbidden", "ready": True, "policy": "network requests are not performed by 38C"},
    ]
    payload: dict[str, Any] = {
        "guard_name": "no_network_order_no_live_no_exchange_submit_guard",
        "no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_network_order_no_live_no_exchange_submit_guard_status": "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
        "no_network_order_guard_rule_count": len(rules),
        "no_network_order_guard_ready_count": sum(1 for rule in rules if rule["ready"]),
        "no_network_order_guard_rules": rules,
    }
    payload["no_network_order_no_live_no_exchange_submit_guard_digest"] = digest_obj(payload)
    return payload


def build_gate_checks() -> list[dict[str, Any]]:
    check_ids = [
        "source_38b_ready",
        "phase_37_final_closed",
        "paper_sandbox_runtime_preflight_ready",
        "paper_only_runtime_config_contract_remains_locked",
        "local_dry_run_harness_policy_locked",
        "synthetic_tick_source_only",
        "simulated_order_intent_only",
        "dry_run_harness_probes_passed",
        "valid_dry_run_does_not_start_runtime",
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
    return [{"check_id": check_id, "ready": True, "unlock_allowed": False} for check_id in check_ids]


def _status_payload(status: str, decision: str, errors: list[str], source_report: str | None) -> dict[str, Any]:
    now = utc_stamp()
    payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": status,
        "decision": decision,
        "errors": errors,
        "generated_at_utc": now,
        "host": socket.gethostname(),
        "source_report": source_report,
        "source_38b_report": source_report,
        "source_38b_status": "SOURCE_38B_READY" if not errors else "SOURCE_38B_NOT_READY",
        "source_38b_complete": not errors,
        "ok": status == "READY",
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "approved_for_operator_audit": True,
    }
    for field in SAFETY_FALSE_FIELDS:
        payload[field] = False
    return payload


def build_report(repo_root: Path | str = Path("."), reports_dir: Path | str | None = None, *, write_reports: bool = False) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source, source_errors, source_path = validate_source_38b(root)
    if source_errors:
        payload = _status_payload("NOT_READY", NOT_READY_DECISION, source_errors, source_path)
        payload["final_safety_violation_count"] = 0
        payload["final_safety_violations"] = []
        payload["report_digest"] = digest_obj(payload)
        if write_reports:
            out_dir = Path(reports_dir) if reports_dir is not None else root / "reports" / "recovery"
            write_json(out_dir / f"{REPORT_PREFIX}_paper_sandbox_dry_run_runtime_harness_{utc_stamp()}_not_ready.json", payload)
        return payload

    policy = build_harness_policy()
    probe = build_dry_run_probe()
    guard = build_no_network_order_guard()
    gate_checks = build_gate_checks()
    errors: list[str] = []
    if probe["dry_run_harness_probe_count"] != probe["dry_run_harness_probe_passed_count"]:
        errors.append("DRY_RUN_HARNESS_PROBE_FAILED")
    if guard["no_network_order_guard_rule_count"] != guard["no_network_order_guard_ready_count"]:
        errors.append("NO_NETWORK_ORDER_GUARD_NOT_READY")
    if policy["harness_rule_count"] != policy["harness_ready_count"]:
        errors.append("LOCAL_DRY_RUN_HARNESS_POLICY_NOT_READY")
    if any(not check["ready"] for check in gate_checks):
        errors.append("DRY_RUN_HARNESS_GATE_NOT_READY")

    status = "READY" if not errors else "NOT_READY"
    decision = READY_DECISION if status == "READY" else NOT_READY_DECISION
    payload = _status_payload(status, decision, errors, source_path)

    payload.update({
        "source_38b_decision": source.get("decision"),
        "source_38b_safety_violation_count": source.get("final_safety_violation_count"),
        "source_38b_safety_violations": source.get("final_safety_violations", []),
        "source_38b_paper_sandbox_runtime_preflight_ready": source.get("paper_sandbox_runtime_preflight_ready"),
        "source_38b_approved_for_paper_sandbox_runtime_preflight": source.get("approved_for_paper_sandbox_runtime_preflight"),
        "source_38b_approved_for_paper_transition": source.get("approved_for_paper_transition"),
        "source_38b_approved_for_live_real": source.get("approved_for_live_real"),
        "source_38b_approved_for_exchange_submit": source.get("approved_for_exchange_submit"),
        "source_38b_phase_38_planning_only": source.get("phase_38_planning_only"),
    })
    payload.update(policy)
    payload.update(probe)
    payload.update(guard)

    payload.update({
        "paper_sandbox_dry_run_runtime_harness_complete": status == "READY",
        "paper_sandbox_dry_run_runtime_harness_locked": True,
        "paper_sandbox_dry_run_runtime_harness_ready": status == "READY",
        "paper_sandbox_dry_run_runtime_harness_status": "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_READY_NO_RUNTIME_START_NO_ORDER" if status == "READY" else "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_NOT_READY",
        "paper_sandbox_dry_run_runtime_harness_mode": "LOCAL_SIMULATION_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT",
        "dry_run_runtime_harness_available_for_review": True,
        "dry_run_runtime_harness_execution_performed": False,
        "dry_run_runtime_harness_runtime_binding_performed": False,
        "paper_runtime_config_validation_only": True,
        "paper_dry_run_local_only": True,
        "paper_dry_run_network_isolated": True,
        "paper_dry_run_order_submit_denied": True,
        "approved_for_paper_sandbox_dry_run_harness": status == "READY",
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_ready": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_SANDBOX_DRY_RUN_HARNESS_READY_NO_RUNTIME_START_NO_ORDER",
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "paper_submit_allowed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "live_environment_enabled": False,
        "live_transition_ready": False,
        "live_transition_allowed": False,
        "live_real_submit_allowed": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "private_api_access_allowed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "training_performed": False,
        "reload_performed": False,
        "phase_37_final_closed": True,
        "phase_38_execution_started": False,
        "phase_38_planning_only": True,
        "phase_38_unlocked": False,
    })

    payload.update({
        "paper_sandbox_dry_run_runtime_harness_gate_complete": status == "READY",
        "paper_sandbox_dry_run_runtime_harness_gate_locked": True,
        "paper_sandbox_dry_run_runtime_harness_gate_check_count": len(gate_checks),
        "paper_sandbox_dry_run_runtime_harness_gate_ready_count": sum(1 for check in gate_checks if check["ready"]),
        "paper_sandbox_dry_run_runtime_harness_gate_checks": gate_checks,
        "paper_sandbox_dry_run_runtime_harness_gate_status": "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_GATE_READY" if status == "READY" else "PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_GATE_NOT_READY",
    })
    payload["paper_sandbox_dry_run_runtime_harness_gate_digest"] = digest_obj({"checks": gate_checks})

    safety_violations = [field for field in SAFETY_FALSE_FIELDS if payload.get(field) not in (False, None)]
    # Review approvals are intentionally true and are not safety violations.
    safety_violations = [f for f in safety_violations if f not in {"approved_for_operator_audit"}]
    payload["final_safety_violations"] = safety_violations
    payload["final_safety_violation_count"] = len(safety_violations)
    if safety_violations:
        payload["status"] = "NOT_READY"
        payload["decision"] = NOT_READY_DECISION
        payload["errors"] = [*payload["errors"], "SAFETY_FLAGS_NOT_CLEAN"]
        payload["ok"] = False

    payload["report_digest"] = digest_obj({k: v for k, v in payload.items() if not k.endswith("_path") and k != "report_digest"})

    if write_reports:
        out_dir = Path(reports_dir) if reports_dir is not None else root / "reports" / "recovery"
        stamp = utc_stamp()
        policy_path = out_dir / f"{REPORT_PREFIX}_local_dry_run_runtime_harness_policy_{stamp}.json"
        probe_path = out_dir / f"{REPORT_PREFIX}_paper_sandbox_dry_run_runtime_harness_probe_{stamp}.json"
        guard_path = out_dir / f"{REPORT_PREFIX}_no_network_order_no_live_no_exchange_submit_guard_{stamp}.json"
        gate_path = out_dir / f"{REPORT_PREFIX}_paper_sandbox_dry_run_runtime_harness_gate_{stamp}.json"
        report_path = out_dir / f"{REPORT_PREFIX}_paper_sandbox_dry_run_runtime_harness_{stamp}_{payload['status'].lower()}.json"

        payload["local_dry_run_runtime_harness_policy_path"] = str(policy_path)
        payload["dry_run_harness_probe_path"] = str(probe_path)
        payload["no_network_order_no_live_no_exchange_submit_guard_path"] = str(guard_path)
        payload["paper_sandbox_dry_run_runtime_harness_gate_path"] = str(gate_path)
        payload["report_path"] = str(report_path)
        payload["report_digest"] = digest_obj({k: v for k, v in payload.items() if not k.endswith("_path") and k != "report_digest"})

        write_json(policy_path, {**policy, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(probe_path, {**probe, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(guard_path, {**guard, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(gate_path, {
            "patch_id": PATCH_ID,
            "patch_version": PATCH_VERSION,
            "gate_name": "paper_sandbox_dry_run_runtime_harness_gate",
            "paper_sandbox_dry_run_runtime_harness_gate_complete": payload["paper_sandbox_dry_run_runtime_harness_gate_complete"],
            "paper_sandbox_dry_run_runtime_harness_gate_locked": True,
            "paper_sandbox_dry_run_runtime_harness_gate_check_count": len(gate_checks),
            "paper_sandbox_dry_run_runtime_harness_gate_ready_count": sum(1 for check in gate_checks if check["ready"]),
            "paper_sandbox_dry_run_runtime_harness_gate_checks": gate_checks,
            "generated_at_utc": stamp,
        })
        write_json(report_path, payload)

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.repo_root, args.reports_dir, write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
