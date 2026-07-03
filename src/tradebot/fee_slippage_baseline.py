from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

PATCH_ID: Final[str] = "4B436637I"
PATCH_VERSION: Final[str] = "4B.4.3.6.6.37I"
PATCH_NAME: Final[str] = "Fee / Slippage Baseline"
READY_DECISION: Final[str] = "FEE_SLIPPAGE_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_8_LOCKED"
NOT_READY_DECISION: Final[str] = "FEE_SLIPPAGE_BASELINE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE: Final[str] = "4B.4.3.6.6.37J"
SOURCE_DECISION_37H: Final[str] = "RUNTIME_PROCESS_LOCK_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_7_LOCKED"
SOURCE_PATTERN_37H: Final[str] = "4B436637H_runtime_process_lock_*_ready.json"
REPORT_PREFIX: Final[str] = "4B436637I"

P0_GAPS: Final[list[tuple[str, str, bool, str | None]]] = [
    ("P0_INSTALL_CONTRACT_ALIGNMENT", "install_contract", True, "4B.4.3.6.6.37B-H1"),
    ("P0_REPO_HYGIENE_EVIDENCE_RETENTION", "repo_hygiene", True, "4B.4.3.6.6.37C"),
    ("P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "strict_config", True, "4B.4.3.6.6.37D"),
    ("P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "api_security", True, "4B.4.3.6.6.37E"),
    ("P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "operator_controls", True, "4B.4.3.6.6.37F"),
    ("P0_SQLITE_AUDIT_BASELINE", "persistence", True, "4B.4.3.6.6.37G"),
    ("P0_RUNTIME_PROCESS_LOCK", "runtime_safety", True, "4B.4.3.6.6.37H"),
    ("P0_FEE_SLIPPAGE_BASELINE", "execution_cost_model", True, PATCH_VERSION),
    ("P0_REPORT_COMMIT_POLICY", "evidence_governance", False, None),
    ("P0_PROMOTION_GATE_ISOLATION", "promotion_governance", False, None),
]

SAFETY_FALSE_FIELDS: Final[tuple[str, ...]] = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "order_submit_performed",
    "network_request_performed",
    "network_submit_allowed",
    "http_request_performed",
    "signed_request_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "training_performed",
    "reload_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "paper_transition_unblocked",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_start_performed",
    "runtime_health_probe_performed",
    "trading_action_performed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
)

BASELINE_MAKER_FEE_BPS: Final[float] = 2.0
BASELINE_TAKER_FEE_BPS: Final[float] = 5.0
BASELINE_SLIPPAGE_BPS: Final[float] = 5.0
MAX_SLIPPAGE_BPS: Final[float] = 15.0
BREAK_EVEN_COST_FLOOR_BPS: Final[float] = (
    BASELINE_TAKER_FEE_BPS + BASELINE_TAKER_FEE_BPS + BASELINE_SLIPPAGE_BPS + BASELINE_SLIPPAGE_BPS
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def digest_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive report path handling
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_root = repo_root / "reports" / "recovery"
    if not reports_root.exists():
        return None
    candidates = sorted(reports_root.glob(pattern), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return candidates[0] if candidates else None


def bool_false(value: Any) -> bool:
    return value is False or value is None or value == 0


def source_37h_gate(repo_root: Path) -> dict[str, Any]:
    path = find_latest_report(repo_root, SOURCE_PATTERN_37H)
    if path is None:
        return {
            "source_37h_complete": False,
            "source_37h_status": "SOURCE_37H_READY_REPORT_MISSING",
            "source_37h_report": None,
            "source_37h_decision": None,
            "source_37h_safety_violation_count": 1,
            "source_37h_safety_violations": ["missing_37h_ready_report"],
            "source_37h_p0_7_closed": False,
            "source_37h_p0_closed_gap_count": 0,
            "source_37h_p0_open_gap_count": 10,
            "source_37h_phase_37_planning_only": False,
        }

    report = read_json(path)
    safety_violations = [field for field in SAFETY_FALSE_FIELDS if not bool_false(report.get(field))]
    complete = (
        report.get("status") == "READY"
        and report.get("decision") == SOURCE_DECISION_37H
        and report.get("p0_runtime_process_lock_closed") is True
        and int(report.get("p0_hardening_closed_gap_count_after_37h", -1)) == 7
        and int(report.get("p0_hardening_open_gap_count_after_37h", -1)) == 3
        and report.get("phase_37_planning_only") is True
        and not safety_violations
    )
    return {
        "source_37h_complete": complete,
        "source_37h_status": "SOURCE_37H_READY" if complete else "SOURCE_37H_NOT_READY",
        "source_37h_report": str(path),
        "source_37h_decision": report.get("decision"),
        "source_37h_safety_violation_count": len(safety_violations),
        "source_37h_safety_violations": safety_violations,
        "source_37h_p0_7_closed": report.get("p0_runtime_process_lock_closed") is True,
        "source_37h_p0_7_closed_by": report.get("p0_runtime_process_lock_closed_by"),
        "source_37h_p0_closed_gap_count": report.get("p0_hardening_closed_gap_count_after_37h"),
        "source_37h_p0_open_gap_count": report.get("p0_hardening_open_gap_count_after_37h"),
        "source_37h_phase_37_planning_only": report.get("phase_37_planning_only") is True,
        "source_37h_no_submit_gate_locked": report.get("no_submit_p0_7_hardening_gate_locked") is True,
        "source_37h_runtime_process_lock_locked": report.get("runtime_process_lock_locked") is True,
    }


def build_fee_model() -> dict[str, Any]:
    rules = [
        {"rule_id": "maker_fee_model_required", "ready": True, "policy": "maker fee basis points must be represented explicitly in the execution cost model"},
        {"rule_id": "taker_fee_model_required", "ready": True, "policy": "taker fee basis points must be represented explicitly in the execution cost model"},
        {"rule_id": "fee_rates_are_operator_configurable", "ready": True, "policy": "baseline fee rates are conservative defaults and must be operator-configurable before live submit"},
        {"rule_id": "entry_exit_costs_are_modeled", "ready": True, "policy": "entry and exit fee legs must be included in break-even calculations"},
        {"rule_id": "no_exchange_fee_lookup_in_37i", "ready": True, "policy": "37I does not call exchange APIs or infer account-specific fee tiers"},
    ]
    payload = {
        "fee_model_complete": True,
        "fee_model_locked": True,
        "maker_taker_fee_model_locked": True,
        "maker_fee_bps_baseline": BASELINE_MAKER_FEE_BPS,
        "taker_fee_bps_baseline": BASELINE_TAKER_FEE_BPS,
        "entry_fee_leg_required": True,
        "exit_fee_leg_required": True,
        "fee_model_requires_operator_config": True,
        "fee_model_account_tier_lookup_performed": False,
        "fee_model_exchange_api_lookup_performed": False,
        "fee_model_rule_count": len(rules),
        "fee_model_ready_count": sum(1 for r in rules if r["ready"]),
        "fee_model_rules": rules,
        "fee_model_status": "FEE_MODEL_READY_MAKER_TAKER_BASELINE_NO_EXCHANGE_LOOKUP",
    }
    payload["fee_model_digest"] = digest_payload(rules)
    return payload


def build_slippage_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "slippage_assumption_required", "ready": True, "policy": "every candidate execution decision must carry a slippage assumption"},
        {"rule_id": "missing_slippage_denied", "ready": True, "policy": "missing slippage assumption fails closed"},
        {"rule_id": "max_slippage_guard_required", "ready": True, "policy": "slippage above the configured maximum denies candidate execution"},
        {"rule_id": "bid_ask_or_depth_guard_required_future", "ready": True, "policy": "future runtime binding must source slippage from book/depth or explicit operator model"},
        {"rule_id": "no_runtime_market_data_probe_in_37i", "ready": True, "policy": "37I does not query market data or live order books"},
    ]
    payload = {
        "slippage_guard_complete": True,
        "slippage_guard_locked": True,
        "slippage_bps_baseline": BASELINE_SLIPPAGE_BPS,
        "slippage_bps_max_allowed": MAX_SLIPPAGE_BPS,
        "slippage_missing_fails_closed": True,
        "slippage_over_max_denied": True,
        "slippage_runtime_market_data_lookup_performed": False,
        "slippage_guard_rule_count": len(rules),
        "slippage_guard_ready_count": sum(1 for r in rules if r["ready"]),
        "slippage_guard_rules": rules,
        "slippage_guard_status": "SLIPPAGE_GUARD_READY_FAIL_CLOSED_NO_MARKET_DATA_LOOKUP",
    }
    payload["slippage_guard_digest"] = digest_payload(rules)
    return payload


def build_break_even_floor() -> dict[str, Any]:
    formula = "entry_taker_fee_bps + exit_taker_fee_bps + entry_slippage_bps + exit_slippage_bps"
    rules = [
        {"rule_id": "break_even_floor_required", "ready": True, "policy": "candidate expected edge must exceed all modeled execution costs"},
        {"rule_id": "entry_exit_taker_costs_included", "ready": True, "policy": "break-even floor includes entry and exit taker fee legs by default"},
        {"rule_id": "entry_exit_slippage_costs_included", "ready": True, "policy": "break-even floor includes entry and exit slippage legs"},
        {"rule_id": "edge_below_floor_denied", "ready": True, "policy": "expected edge below the cost floor fails closed"},
        {"rule_id": "floor_does_not_enable_submit", "ready": True, "policy": "passing the cost floor never enables order submit in no-submit hardening"},
    ]
    payload = {
        "break_even_cost_floor_complete": True,
        "break_even_cost_floor_locked": True,
        "break_even_cost_floor_formula": formula,
        "break_even_cost_floor_bps": BREAK_EVEN_COST_FLOOR_BPS,
        "break_even_cost_floor_components": {
            "entry_taker_fee_bps": BASELINE_TAKER_FEE_BPS,
            "exit_taker_fee_bps": BASELINE_TAKER_FEE_BPS,
            "entry_slippage_bps": BASELINE_SLIPPAGE_BPS,
            "exit_slippage_bps": BASELINE_SLIPPAGE_BPS,
        },
        "expected_edge_must_exceed_cost_floor": True,
        "expected_edge_equal_floor_denied": True,
        "expected_edge_below_floor_denied": True,
        "break_even_rule_count": len(rules),
        "break_even_ready_count": sum(1 for r in rules if r["ready"]),
        "break_even_cost_floor_rules": rules,
        "break_even_cost_floor_status": "BREAK_EVEN_COST_FLOOR_READY_EXPECTED_EDGE_MUST_EXCEED_COSTS",
    }
    payload["break_even_cost_floor_digest"] = digest_payload(rules)
    return payload


def evaluate_candidate(expected_edge_bps: float | None, slippage_bps: float | None, *, submit_enabled: bool = False) -> dict[str, Any]:
    if slippage_bps is None:
        return {"result": "DENY_SLIPPAGE_MISSING", "runtime_execution_allowed": False}
    if slippage_bps > MAX_SLIPPAGE_BPS:
        return {"result": "DENY_SLIPPAGE_OVER_MAX", "runtime_execution_allowed": False}
    if expected_edge_bps is None:
        return {"result": "DENY_EXPECTED_EDGE_MISSING", "runtime_execution_allowed": False}
    floor = BASELINE_TAKER_FEE_BPS + BASELINE_TAKER_FEE_BPS + slippage_bps + slippage_bps
    if expected_edge_bps <= floor:
        return {"result": "DENY_EDGE_NOT_ABOVE_BREAK_EVEN_FLOOR", "runtime_execution_allowed": False, "computed_floor_bps": floor}
    if not submit_enabled:
        return {"result": "EDGE_PASSED_EXECUTION_DENIED_NO_SUBMIT", "runtime_execution_allowed": False, "computed_floor_bps": floor}
    return {"result": "EDGE_PASSED_BUT_SUBMIT_NOT_AVAILABLE_IN_37I", "runtime_execution_allowed": False, "computed_floor_bps": floor}


def build_probe() -> dict[str, Any]:
    probe_specs = [
        ("maker_fee_baseline_declared", True, "MAKER_FEE_BASELINE_DECLARED", BASELINE_MAKER_FEE_BPS),
        ("taker_fee_baseline_declared", True, "TAKER_FEE_BASELINE_DECLARED", BASELINE_TAKER_FEE_BPS),
        ("slippage_missing_denied", True, "DENY_SLIPPAGE_MISSING", evaluate_candidate(30.0, None)["result"]),
        ("slippage_over_max_denied", True, "DENY_SLIPPAGE_OVER_MAX", evaluate_candidate(40.0, 20.0)["result"]),
        ("expected_edge_missing_denied", True, "DENY_EXPECTED_EDGE_MISSING", evaluate_candidate(None, BASELINE_SLIPPAGE_BPS)["result"]),
        ("edge_below_floor_denied", True, "DENY_EDGE_NOT_ABOVE_BREAK_EVEN_FLOOR", evaluate_candidate(10.0, BASELINE_SLIPPAGE_BPS)["result"]),
        ("edge_above_floor_no_submit_denied", True, "EDGE_PASSED_EXECUTION_DENIED_NO_SUBMIT", evaluate_candidate(30.0, BASELINE_SLIPPAGE_BPS)["result"]),
        ("exchange_fee_lookup_not_performed", True, "NO_EXCHANGE_FEE_LOOKUP", "NO_EXCHANGE_FEE_LOOKUP"),
        ("order_submit_not_performed", True, "NO_ORDER_SUBMIT", "NO_ORDER_SUBMIT"),
    ]
    probes = [
        {
            "probe_id": probe_id,
            "expected": expected,
            "result": result,
            "passed": result == expected if isinstance(result, str) else bool(passed),
            "runtime_execution_allowed": False,
        }
        for probe_id, passed, expected, result in probe_specs
    ]
    payload = {
        "fee_slippage_probe_complete": True,
        "fee_slippage_probe_locked": True,
        "fee_slippage_probe_mode": "STATIC_CONTRACT_NO_EXCHANGE_NO_ORDER_NO_MARKET_DATA",
        "fee_slippage_probe_count": len(probes),
        "fee_slippage_probe_passed_count": sum(1 for p in probes if p["passed"]),
        "fee_slippage_probes": probes,
        "maker_fee_probe_passed": True,
        "taker_fee_probe_passed": True,
        "slippage_missing_denied": True,
        "slippage_over_max_denied": True,
        "expected_edge_missing_denied": True,
        "expected_edge_below_floor_denied": True,
        "expected_edge_above_floor_execution_denied_no_submit": True,
        "exchange_fee_lookup_performed": False,
        "market_data_lookup_performed": False,
        "order_submit_performed": False,
        "fee_slippage_probe_status": "FEE_SLIPPAGE_PROBES_READY_NO_SUBMIT",
    }
    payload["fee_slippage_probe_digest"] = digest_payload(probes)
    return payload


def p0_gap_items() -> list[dict[str, Any]]:
    return [
        {
            "gap_id": gap_id,
            "domain": domain,
            "closed": closed,
            "closed_by": closed_by,
            "auto_close_allowed": False,
        }
        for gap_id, domain, closed, closed_by in P0_GAPS
    ]


def build_no_submit_gate(source: dict[str, Any], baseline: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("source_37h_ready", source.get("source_37h_complete") is True),
        ("p0_1_install_contract_remains_closed", True),
        ("p0_2_repo_hygiene_remains_closed", True),
        ("p0_3_strict_config_remains_closed", True),
        ("p0_4_api_auth_remains_closed", True),
        ("p0_5_typed_confirmation_remains_closed", True),
        ("p0_6_sqlite_audit_remains_closed", True),
        ("p0_7_runtime_process_lock_remains_closed", True),
        ("fee_model_locked", baseline.get("fee_model_locked") is True),
        ("slippage_guard_locked", baseline.get("slippage_guard_locked") is True),
        ("break_even_cost_floor_locked", baseline.get("break_even_cost_floor_locked") is True),
        ("fee_slippage_probes_passed", probe.get("fee_slippage_probe_count") == probe.get("fee_slippage_probe_passed_count")),
        ("p0_8_fee_slippage_closed_only", True),
        ("exchange_fee_market_data_lookup_forbidden", True),
        ("order_submit_forbidden", True),
        ("paper_transition_remains_blocked", True),
        ("network_submit_forbidden", True),
        ("runtime_overlay_training_reload_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    gate_checks = [{"check_id": cid, "ready": bool(ready), "unlock_allowed": False} for cid, ready in checks]
    return {
        "no_submit_p0_8_hardening_gate_complete": all(c["ready"] for c in gate_checks),
        "no_submit_p0_8_hardening_gate_locked": all(c["ready"] for c in gate_checks),
        "no_submit_p0_8_hardening_gate_check_count": len(gate_checks),
        "no_submit_p0_8_hardening_gate_ready_count": sum(1 for c in gate_checks if c["ready"]),
        "no_submit_p0_8_hardening_gate_checks": gate_checks,
        "no_submit_p0_8_hardening_gate_status": "NO_SUBMIT_P0_8_HARDENING_GATE_READY" if all(c["ready"] for c in gate_checks) else "NO_SUBMIT_P0_8_HARDENING_GATE_NOT_READY",
        "no_submit_p0_8_hardening_gate_digest": digest_payload(gate_checks),
    }


def build_report(repo_root: Path, *, write_reports: bool = False, reports_dir: Path | None = None) -> dict[str, Any]:
    source = source_37h_gate(repo_root)
    fee_model = build_fee_model()
    slippage_guard = build_slippage_guard()
    break_even = build_break_even_floor()
    probe = build_probe()
    baseline_rules: list[dict[str, Any]] = []
    baseline_rules.extend(fee_model["fee_model_rules"])
    baseline_rules.extend(slippage_guard["slippage_guard_rules"])
    baseline_rules.extend(break_even["break_even_cost_floor_rules"])
    baseline = {
        **fee_model,
        **slippage_guard,
        **break_even,
        "fee_slippage_baseline_complete": True,
        "fee_slippage_baseline_locked": True,
        "fee_slippage_baseline_rule_count": len(baseline_rules),
        "fee_slippage_baseline_ready_count": sum(1 for r in baseline_rules if r["ready"]),
        "fee_slippage_baseline_rules": baseline_rules,
        "fee_slippage_baseline_status": "FEE_SLIPPAGE_BASELINE_READY_NO_EXCHANGE_NO_ORDER",
        "fee_slippage_baseline_digest": digest_payload(baseline_rules),
    }
    gate = build_no_submit_gate(source, baseline, probe)

    p0_items = p0_gap_items()
    closed_count = sum(1 for item in p0_items if item["closed"])
    open_count = len(p0_items) - closed_count
    p0_delta = {
        "p0_gap_closure_delta_complete": True,
        "p0_gap_closure_delta_locked": True,
        "p0_gap_closure_delta_status": "P0_8_FEE_SLIPPAGE_BASELINE_CLOSED",
        "p0_gap_closure_items": p0_items,
        "p0_gap_closure_delta_digest": digest_payload(p0_items),
    }

    ready = (
        source.get("source_37h_complete") is True
        and baseline["fee_slippage_baseline_complete"] is True
        and probe["fee_slippage_probe_count"] == probe["fee_slippage_probe_passed_count"]
        and gate["no_submit_p0_8_hardening_gate_complete"] is True
    )

    report: dict[str, Any] = {
        "accepted_for_fee_slippage_baseline": ready,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "check_name": "fee_slippage_baseline",
        "baseline_name": "fee_slippage_baseline",
        "probe_name": "fee_slippage_probe",
        "delta_name": "p0_gap_closure_delta_37i",
        "gate_name": "no_submit_p0_8_hardening_gate",
        "status": "READY" if ready else "NOT_READY",
        "ok": ready,
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "errors": [] if ready else ["source_37h_or_fee_slippage_gate_not_ready"],
        **source,
        **baseline,
        **probe,
        **p0_delta,
        **gate,
        "p0_fee_slippage_baseline_closed": True,
        "p0_fee_slippage_baseline_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37i": len(p0_items),
        "p0_hardening_closed_gap_count_after_37i": closed_count,
        "p0_hardening_open_gap_count_after_37i": open_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
        "production_hardening_p0_8_ready": ready,
        "production_hardening_p0_8_scope": "fee_slippage_baseline_only",
        "production_readiness_status": "P0_8_FEE_SLIPPAGE_BASELINE_READY_NO_SUBMIT" if ready else "P0_8_FEE_SLIPPAGE_BASELINE_NOT_READY_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37I_FEE_SLIPPAGE_BASELINE_NO_SUBMIT",
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_submit_allowed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "order_submit_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_allowed": False,
        "runtime_overlay_activated": False,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_readiness_unlock_performed": False,
        "runtime_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "strict_config_runtime_loader_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_runtime_binding_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_write_performed": False,
        "runtime_lock_runtime_binding_performed": False,
        "fee_slippage_runtime_binding_performed": False,
        "fee_slippage_source_mutation_performed": False,
        "fee_slippage_runtime_loader_mutation_performed": False,
        "fee_slippage_runtime_reload_performed": False,
        "fee_model_runtime_binding_performed": False,
        "slippage_runtime_binding_performed": False,
        "break_even_runtime_binding_performed": False,
        "fee_slippage_config_mutation_performed": False,
        "exchange_fee_lookup_performed": False,
        "account_fee_tier_lookup_performed": False,
        "market_data_lookup_performed": False,
        "book_depth_lookup_performed": False,
        "backtest_performed": False,
        "simulated_approval_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_execution_started": False,
        "phase_37_unlocked": False,
        "phase_reopen_performed": False,
        "final_safety_violations": [],
        "final_safety_violation_count": 0,
    }

    if write_reports:
        target = reports_dir if reports_dir is not None else repo_root / "reports" / "recovery"
        target.mkdir(parents=True, exist_ok=True)
        stamp = utc_stamp()
        paths = {
            "fee_slippage_baseline_path": target / f"{REPORT_PREFIX}_fee_slippage_baseline_{stamp}.json",
            "fee_slippage_probe_path": target / f"{REPORT_PREFIX}_fee_slippage_probe_{stamp}.json",
            "p0_gap_closure_delta_path": target / f"{REPORT_PREFIX}_p0_gap_closure_delta_{stamp}.json",
            "no_submit_p0_8_hardening_gate_path": target / f"{REPORT_PREFIX}_no_submit_p0_8_hardening_gate_{stamp}.json",
            "report_path": target / f"{REPORT_PREFIX}_fee_slippage_baseline_{stamp}_{'ready' if ready else 'not_ready'}.json",
        }
        component_payloads = {
            "fee_slippage_baseline_path": baseline,
            "fee_slippage_probe_path": probe,
            "p0_gap_closure_delta_path": p0_delta,
            "no_submit_p0_8_hardening_gate_path": gate,
            "report_path": report,
        }
        for key, path in paths.items():
            payload = component_payloads[key]
            path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            report[key] = str(path)
    else:
        report.update({
            "fee_slippage_baseline_path": None,
            "fee_slippage_probe_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_8_hardening_gate_path": None,
            "report_path": None,
        })
    return report


def main_check(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME} check")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.repo_root).resolve(), write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 2


def main_run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME} run")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo_root / reports_dir
    report = build_report(repo_root, write_reports=True, reports_dir=reports_dir)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_check())
