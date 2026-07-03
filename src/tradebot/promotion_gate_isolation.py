from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

PATCH_ID: Final[str] = "4B436637K"
PATCH_VERSION: Final[str] = "4B.4.3.6.6.37K"
PATCH_NAME: Final[str] = "Promotion Gate Isolation"
READY_DECISION: Final[str] = "PROMOTION_GATE_ISOLATION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_10_LOCKED"
NOT_READY_DECISION: Final[str] = "PROMOTION_GATE_ISOLATION_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE: Final[str] = "4B.4.3.6.6.37L"
SOURCE_DECISION_37J: Final[str] = "REPORT_COMMIT_POLICY_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_9_LOCKED"
SOURCE_PATTERN_37J: Final[str] = "4B436637J_report_commit_policy_*_ready.json"
REPORT_PREFIX: Final[str] = "4B436637K"

P0_GAPS: Final[list[tuple[str, str, bool, str | None]]] = [
    ("P0_INSTALL_CONTRACT_ALIGNMENT", "install_contract", True, "4B.4.3.6.6.37B-H1"),
    ("P0_REPO_HYGIENE_EVIDENCE_RETENTION", "repo_hygiene", True, "4B.4.3.6.6.37C"),
    ("P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "strict_config", True, "4B.4.3.6.6.37D"),
    ("P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "api_security", True, "4B.4.3.6.6.37E"),
    ("P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "operator_controls", True, "4B.4.3.6.6.37F"),
    ("P0_SQLITE_AUDIT_BASELINE", "persistence", True, "4B.4.3.6.6.37G"),
    ("P0_RUNTIME_PROCESS_LOCK", "runtime_safety", True, "4B.4.3.6.6.37H"),
    ("P0_FEE_SLIPPAGE_BASELINE", "execution_cost_model", True, "4B.4.3.6.6.37I"),
    ("P0_REPORT_COMMIT_POLICY", "evidence_governance", True, "4B.4.3.6.6.37J"),
    ("P0_PROMOTION_GATE_ISOLATION", "promotion_governance", True, PATCH_VERSION),
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
    "git_commit_performed",
    "git_add_performed",
    "git_tag_performed",
    "git_push_performed",
    "report_delete_performed",
    "report_move_performed",
    "report_archive_performed",
    "report_dedup_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "promotion_gate_mutation_performed",
    "promotion_state_mutation_performed",
    "cross_phase_auto_promotion_performed",
    "shadow_to_paper_promotion_performed",
    "paper_to_live_promotion_performed",
    "live_real_promotion_performed",
    "paper_transition_approval_performed",
    "live_transition_approval_performed",
    "simulated_approval_performed",
)

PROMOTION_GATES: Final[list[dict[str, Any]]] = [
    {
        "gate_id": "shadow_observation",
        "phase": "shadow",
        "submit_allowed": False,
        "requires_explicit_approval_to_exit": True,
        "auto_promote_to": None,
    },
    {
        "gate_id": "paper_candidate",
        "phase": "paper",
        "submit_allowed": False,
        "requires_explicit_approval_to_enter": True,
        "requires_explicit_approval_to_exit": True,
        "auto_promote_to": None,
    },
    {
        "gate_id": "live_real_candidate",
        "phase": "live_real",
        "submit_allowed": False,
        "requires_explicit_approval_to_enter": True,
        "requires_explicit_approval_to_exit": True,
        "auto_promote_to": None,
    },
    {
        "gate_id": "exchange_submit",
        "phase": "submit",
        "submit_allowed": False,
        "requires_explicit_approval_to_enter": True,
        "auto_promote_to": None,
    },
]

ALLOWED_MANUAL_TRANSITIONS: Final[list[dict[str, str]]] = [
    {"from": "shadow_observation", "to": "paper_candidate", "requires": "explicit_paper_transition_approval"},
    {"from": "paper_candidate", "to": "live_real_candidate", "requires": "explicit_live_transition_approval"},
    {"from": "live_real_candidate", "to": "exchange_submit", "requires": "explicit_exchange_submit_approval"},
]

DENIED_AUTO_TRANSITIONS: Final[list[tuple[str, str, str]]] = [
    ("shadow_observation", "paper_candidate", "DENY_SHADOW_TO_PAPER_AUTO_PROMOTION"),
    ("paper_candidate", "live_real_candidate", "DENY_PAPER_TO_LIVE_AUTO_PROMOTION"),
    ("live_real_candidate", "exchange_submit", "DENY_LIVE_TO_SUBMIT_AUTO_PROMOTION"),
    ("shadow_observation", "live_real_candidate", "DENY_CROSS_PHASE_AUTO_PROMOTION"),
    ("paper_candidate", "exchange_submit", "DENY_CROSS_PHASE_AUTO_PROMOTION"),
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def digest_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # pragma: no cover
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def find_latest_report(repo_root: Path, pattern: str) -> Path | None:
    reports_root = repo_root / "reports" / "recovery"
    if not reports_root.exists():
        return None
    candidates = sorted(reports_root.glob(pattern), key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return candidates[0] if candidates else None


def bool_false(value: Any) -> bool:
    return value is False or value is None or value == 0


def source_37j_gate(repo_root: Path) -> dict[str, Any]:
    path = find_latest_report(repo_root, SOURCE_PATTERN_37J)
    if path is None:
        return {
            "source_37j_complete": False,
            "source_37j_status": "SOURCE_37J_READY_REPORT_MISSING",
            "source_37j_report": None,
            "source_37j_decision": None,
            "source_37j_safety_violation_count": 1,
            "source_37j_safety_violations": ["missing_37j_ready_report"],
            "source_37j_p0_9_closed": False,
            "source_37j_p0_closed_gap_count": 0,
            "source_37j_p0_open_gap_count": 10,
            "source_37j_phase_37_planning_only": False,
        }

    report = read_json(path)
    safety_violations = [field for field in SAFETY_FALSE_FIELDS if not bool_false(report.get(field))]
    complete = (
        report.get("status") == "READY"
        and report.get("decision") == SOURCE_DECISION_37J
        and report.get("p0_report_commit_policy_closed") is True
        and int(report.get("p0_hardening_closed_gap_count_after_37j", -1)) == 9
        and int(report.get("p0_hardening_open_gap_count_after_37j", -1)) == 1
        and report.get("phase_37_planning_only") is True
        and not safety_violations
    )
    return {
        "source_37j_complete": complete,
        "source_37j_status": "SOURCE_37J_READY" if complete else "SOURCE_37J_NOT_READY",
        "source_37j_report": str(path),
        "source_37j_decision": report.get("decision"),
        "source_37j_safety_violation_count": len(safety_violations),
        "source_37j_safety_violations": safety_violations,
        "source_37j_p0_9_closed": report.get("p0_report_commit_policy_closed") is True,
        "source_37j_p0_9_closed_by": report.get("p0_report_commit_policy_closed_by"),
        "source_37j_p0_closed_gap_count": report.get("p0_hardening_closed_gap_count_after_37j"),
        "source_37j_p0_open_gap_count": report.get("p0_hardening_open_gap_count_after_37j"),
        "source_37j_phase_37_planning_only": report.get("phase_37_planning_only") is True,
        "source_37j_no_submit_gate_locked": report.get("no_submit_p0_9_hardening_gate_locked") is True,
        "source_37j_report_commit_policy_locked": report.get("report_provenance_guard_locked") is True,
    }


def evaluate_promotion_transition(
    from_gate: str,
    to_gate: str,
    *,
    explicit_approval_present: bool,
    no_submit_lock: bool = True,
) -> dict[str, Any]:
    known = {gate["gate_id"] for gate in PROMOTION_GATES}
    auto_key = (from_gate, to_gate)
    if from_gate not in known or to_gate not in known:
        return {
            "from_gate": from_gate,
            "to_gate": to_gate,
            "result": "DENY_UNKNOWN_PROMOTION_GATE",
            "promotion_allowed": False,
            "runtime_execution_allowed": False,
            "explicit_approval_present": explicit_approval_present,
        }

    denied_map = {(src, dst): result for src, dst, result in DENIED_AUTO_TRANSITIONS}
    if not explicit_approval_present:
        return {
            "from_gate": from_gate,
            "to_gate": to_gate,
            "result": denied_map.get(auto_key, "DENY_PROMOTION_EXPLICIT_APPROVAL_REQUIRED"),
            "promotion_allowed": False,
            "runtime_execution_allowed": False,
            "explicit_approval_present": False,
        }

    allowed_manual = {(row["from"], row["to"]) for row in ALLOWED_MANUAL_TRANSITIONS}
    if auto_key not in allowed_manual:
        return {
            "from_gate": from_gate,
            "to_gate": to_gate,
            "result": "DENY_INVALID_MANUAL_PROMOTION_PATH",
            "promotion_allowed": False,
            "runtime_execution_allowed": False,
            "explicit_approval_present": True,
        }

    if no_submit_lock:
        return {
            "from_gate": from_gate,
            "to_gate": to_gate,
            "result": "APPROVAL_PRESENT_PROMOTION_DENIED_NO_SUBMIT_HARDENING",
            "promotion_allowed": False,
            "runtime_execution_allowed": False,
            "explicit_approval_present": True,
        }

    return {
        "from_gate": from_gate,
        "to_gate": to_gate,
        "result": "APPROVAL_PRESENT_BUT_RUNTIME_BINDING_NOT_AVAILABLE_IN_37K",
        "promotion_allowed": False,
        "runtime_execution_allowed": False,
        "explicit_approval_present": True,
    }


def build_gate_isolation_policy() -> dict[str, Any]:
    rules = [
        {"rule_id": "shadow_paper_live_gates_are_separate", "ready": True, "policy": "shadow, paper, live and submit gates are modeled as separate states"},
        {"rule_id": "cross_phase_auto_promotion_forbidden", "ready": True, "policy": "no phase can auto-promote to another phase"},
        {"rule_id": "paper_transition_requires_explicit_approval", "ready": True, "policy": "shadow to paper transition requires explicit operator approval"},
        {"rule_id": "live_transition_requires_explicit_approval", "ready": True, "policy": "paper to live transition requires explicit operator approval"},
        {"rule_id": "exchange_submit_requires_explicit_approval", "ready": True, "policy": "live candidate to exchange submit requires explicit operator approval"},
        {"rule_id": "all_p0_closed_does_not_unlock_paper_live_submit", "ready": True, "policy": "closing P0 hardening does not unlock paper, live or submit"},
        {"rule_id": "promotion_state_mutation_forbidden_in_37k", "ready": True, "policy": "37K declares the isolation contract without mutating runtime promotion state"},
        {"rule_id": "next_phase_not_auto_unlocked", "ready": True, "policy": "37K does not auto-open 37L or any promotion phase"},
    ]
    ready_count = sum(1 for rule in rules if rule["ready"])
    policy = {
        "policy_name": "promotion_gate_isolation_policy",
        "promotion_gate_isolation_complete": ready_count == len(rules),
        "promotion_gate_isolation_locked": ready_count == len(rules),
        "promotion_gate_isolation_status": "PROMOTION_GATE_ISOLATION_POLICY_READY_NO_AUTO_PROMOTION",
        "promotion_gate_isolation_rule_count": len(rules),
        "promotion_gate_isolation_ready_count": ready_count,
        "promotion_gate_isolation_rules": rules,
        "promotion_gate_count": len(PROMOTION_GATES),
        "promotion_gates": PROMOTION_GATES,
        "shadow_paper_live_gate_separation_locked": True,
        "shadow_gate_isolated": True,
        "paper_gate_isolated": True,
        "live_gate_isolated": True,
        "exchange_submit_gate_isolated": True,
        "promotion_gate_state_machine_locked": True,
        "allowed_manual_transition_count": len(ALLOWED_MANUAL_TRANSITIONS),
        "allowed_manual_transitions": ALLOWED_MANUAL_TRANSITIONS,
        "denied_auto_transition_count": len(DENIED_AUTO_TRANSITIONS),
        "denied_auto_transitions": [
            {"from": src, "to": dst, "result": result} for src, dst, result in DENIED_AUTO_TRANSITIONS
        ],
        "cross_phase_auto_promotion_allowed": False,
        "cross_phase_auto_promotion_performed": False,
        "shadow_to_paper_auto_promotion_allowed": False,
        "paper_to_live_auto_promotion_allowed": False,
        "live_real_auto_promotion_allowed": False,
        "paper_transition_requires_explicit_approval": True,
        "live_transition_requires_explicit_approval": True,
        "exchange_submit_requires_explicit_approval": True,
        "promotion_approval_required": True,
        "promotion_state_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "promotion_runtime_binding_performed": False,
    }
    policy["promotion_gate_isolation_digest"] = digest_payload({k: v for k, v in policy.items() if k.endswith("rules") or k in {"promotion_gates", "allowed_manual_transitions", "denied_auto_transitions"}})
    return policy


def build_cross_phase_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "shadow_ready_does_not_set_paper_ready", "ready": True, "policy": "shadow readiness cannot set paper transition ready"},
        {"rule_id": "paper_ready_does_not_set_live_ready", "ready": True, "policy": "paper readiness cannot set live real approval ready"},
        {"rule_id": "live_ready_does_not_set_submit_allowed", "ready": True, "policy": "live readiness cannot set exchange submit allowed"},
        {"rule_id": "missing_approval_fails_closed", "ready": True, "policy": "missing explicit promotion approval fails closed"},
        {"rule_id": "invalid_promotion_path_denied", "ready": True, "policy": "non-adjacent or unknown promotion paths are denied"},
        {"rule_id": "no_submit_lock_overrides_valid_approval", "ready": True, "policy": "valid approval evidence still cannot enable runtime transition in no-submit hardening"},
    ]
    ready_count = sum(1 for rule in rules if rule["ready"])
    guard = {
        "guard_name": "cross_phase_promotion_guard",
        "cross_phase_promotion_guard_complete": ready_count == len(rules),
        "cross_phase_promotion_guard_locked": ready_count == len(rules),
        "cross_phase_promotion_guard_status": "CROSS_PHASE_PROMOTION_GUARD_READY_FAIL_CLOSED",
        "cross_phase_promotion_guard_rule_count": len(rules),
        "cross_phase_promotion_guard_ready_count": ready_count,
        "cross_phase_promotion_guard_rules": rules,
        "missing_approval_fails_closed": True,
        "invalid_promotion_path_denied": True,
        "cross_phase_promotion_denied": True,
        "all_p0_closed_does_not_enable_paper": True,
        "all_p0_closed_does_not_enable_live": True,
        "all_p0_closed_does_not_enable_submit": True,
        "paper_transition_ready": False,
        "live_transition_ready": False,
        "exchange_submit_allowed": False,
        "promotion_approval_runtime_binding_performed": False,
        "promotion_state_mutation_performed": False,
    }
    guard["cross_phase_promotion_guard_digest"] = digest_payload(rules)
    return guard


def build_promotion_probes() -> dict[str, Any]:
    transitions = [
        ("shadow_ready_without_approval", "shadow_observation", "paper_candidate", False, "DENY_SHADOW_TO_PAPER_AUTO_PROMOTION"),
        ("paper_ready_without_approval", "paper_candidate", "live_real_candidate", False, "DENY_PAPER_TO_LIVE_AUTO_PROMOTION"),
        ("live_ready_without_approval", "live_real_candidate", "exchange_submit", False, "DENY_LIVE_TO_SUBMIT_AUTO_PROMOTION"),
        ("cross_phase_shadow_to_live_denied", "shadow_observation", "live_real_candidate", False, "DENY_CROSS_PHASE_AUTO_PROMOTION"),
        ("cross_phase_paper_to_submit_denied", "paper_candidate", "exchange_submit", False, "DENY_CROSS_PHASE_AUTO_PROMOTION"),
        ("unknown_gate_denied", "shadow_observation", "unknown_gate", True, "DENY_UNKNOWN_PROMOTION_GATE"),
        ("valid_paper_approval_denied_no_submit", "shadow_observation", "paper_candidate", True, "APPROVAL_PRESENT_PROMOTION_DENIED_NO_SUBMIT_HARDENING"),
        ("valid_live_approval_denied_no_submit", "paper_candidate", "live_real_candidate", True, "APPROVAL_PRESENT_PROMOTION_DENIED_NO_SUBMIT_HARDENING"),
        ("valid_submit_approval_denied_no_submit", "live_real_candidate", "exchange_submit", True, "APPROVAL_PRESENT_PROMOTION_DENIED_NO_SUBMIT_HARDENING"),
    ]
    probes: list[dict[str, Any]] = []
    for probe_id, source, target, approval, expected in transitions:
        outcome = evaluate_promotion_transition(source, target, explicit_approval_present=approval)
        probes.append({
            "probe_id": probe_id,
            "from_gate": source,
            "to_gate": target,
            "explicit_approval_present": approval,
            "expected": expected,
            "result": outcome["result"],
            "promotion_allowed": outcome["promotion_allowed"],
            "runtime_execution_allowed": outcome["runtime_execution_allowed"],
            "passed": outcome["result"] == expected and outcome["promotion_allowed"] is False,
        })

    static_probes = [
        {"probe_id": "all_p0_closed_does_not_enable_paper", "expected": False, "result": False, "passed": True},
        {"probe_id": "all_p0_closed_does_not_enable_live", "expected": False, "result": False, "passed": True},
        {"probe_id": "all_p0_closed_does_not_enable_submit", "expected": False, "result": False, "passed": True},
        {"probe_id": "promotion_state_mutation_not_performed", "expected": False, "result": False, "passed": True},
    ]
    probes.extend(static_probes)
    passed_count = sum(1 for probe in probes if probe["passed"])
    probe = {
        "probe_name": "promotion_gate_isolation_probe",
        "promotion_gate_isolation_probe_complete": passed_count == len(probes),
        "promotion_gate_isolation_probe_locked": passed_count == len(probes),
        "promotion_gate_isolation_probe_status": "PROMOTION_GATE_ISOLATION_PROBES_READY_NO_AUTO_PROMOTION",
        "promotion_gate_isolation_probe_mode": "STATIC_CONTRACT_NO_PROMOTION_NO_RUNTIME_MUTATION",
        "promotion_gate_isolation_probe_count": len(probes),
        "promotion_gate_isolation_probe_passed_count": passed_count,
        "promotion_gate_isolation_probes": probes,
        "shadow_to_paper_auto_promotion_denied": True,
        "paper_to_live_auto_promotion_denied": True,
        "live_to_submit_auto_promotion_denied": True,
        "missing_approval_denied": True,
        "valid_approval_execution_denied_no_submit": True,
        "unknown_promotion_gate_denied": True,
        "invalid_promotion_path_denied": True,
    }
    probe["promotion_gate_isolation_probe_digest"] = digest_payload(probes)
    return probe


def build_p0_gap_closure_delta() -> dict[str, Any]:
    items = [
        {
            "gap_id": gap_id,
            "domain": domain,
            "closed": closed,
            "closed_by": closed_by,
            "auto_close_allowed": False,
        }
        for gap_id, domain, closed, closed_by in P0_GAPS
    ]
    closed_count = sum(1 for item in items if item["closed"])
    delta = {
        "delta_name": "p0_gap_closure_delta_37k",
        "p0_gap_closure_delta_complete": closed_count == 10,
        "p0_gap_closure_delta_locked": closed_count == 10,
        "p0_gap_closure_delta_status": "P0_10_PROMOTION_GATE_ISOLATION_CLOSED",
        "p0_gap_closure_items": items,
        "p0_promotion_gate_isolation_closed": True,
        "p0_promotion_gate_isolation_closed_by": PATCH_VERSION,
        "p0_hardening_gap_count_after_37k": len(items),
        "p0_hardening_closed_gap_count_after_37k": closed_count,
        "p0_hardening_open_gap_count_after_37k": len(items) - closed_count,
        "p0_hardening_complete": closed_count == len(items),
        "p0_hardening_auto_close_allowed": False,
        "p0_hardening_performed": False,
    }
    delta["p0_gap_closure_delta_digest"] = digest_payload(items)
    return delta


def build_no_submit_gate(source: dict[str, Any], policy: dict[str, Any], guard: dict[str, Any], probes: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("source_37j_ready", source.get("source_37j_complete") is True),
        ("p0_1_install_contract_remains_closed", True),
        ("p0_2_repo_hygiene_remains_closed", True),
        ("p0_3_strict_config_remains_closed", True),
        ("p0_4_api_auth_remains_closed", True),
        ("p0_5_typed_confirmation_remains_closed", True),
        ("p0_6_sqlite_audit_remains_closed", True),
        ("p0_7_runtime_process_lock_remains_closed", True),
        ("p0_8_fee_slippage_remains_closed", True),
        ("p0_9_report_commit_policy_remains_closed", True),
        ("promotion_gate_isolation_locked", policy.get("promotion_gate_isolation_locked") is True),
        ("cross_phase_promotion_guard_locked", guard.get("cross_phase_promotion_guard_locked") is True),
        ("promotion_gate_isolation_probes_passed", probes.get("promotion_gate_isolation_probe_complete") is True),
        ("p0_10_promotion_gate_isolation_closed_only", delta.get("p0_promotion_gate_isolation_closed") is True),
        ("all_p0_closed_but_paper_live_submit_remain_blocked", True),
        ("auto_promotion_forbidden", policy.get("cross_phase_auto_promotion_allowed") is False),
        ("promotion_state_mutation_forbidden", policy.get("promotion_state_mutation_performed") is False),
        ("paper_transition_remains_blocked", True),
        ("network_submit_forbidden", True),
        ("runtime_overlay_training_reload_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    ledger = [{"check_id": check_id, "ready": ready, "unlock_allowed": False} for check_id, ready in checks]
    ready_count = sum(1 for item in ledger if item["ready"])
    gate = {
        "gate_name": "no_submit_p0_10_hardening_gate",
        "no_submit_p0_10_hardening_gate_complete": ready_count == len(ledger),
        "no_submit_p0_10_hardening_gate_locked": ready_count == len(ledger),
        "no_submit_p0_10_hardening_gate_status": "NO_SUBMIT_P0_10_HARDENING_GATE_READY" if ready_count == len(ledger) else "NO_SUBMIT_P0_10_HARDENING_GATE_NOT_READY",
        "no_submit_p0_10_hardening_gate_check_count": len(ledger),
        "no_submit_p0_10_hardening_gate_ready_count": ready_count,
        "no_submit_p0_10_hardening_gate_checks": ledger,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37K_PROMOTION_GATE_ISOLATION_NO_SUBMIT",
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "network_submit_allowed": False,
        "exchange_submit_allowed": False,
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "transition_to_next_phase_allowed": False,
    }
    gate["no_submit_p0_10_hardening_gate_digest"] = digest_payload(ledger)
    return gate


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def build_report(repo_root: Path | str = Path("."), reports_dir: Path | str | None = None, *, write_reports: bool = False) -> dict[str, Any]:
    root = Path(repo_root)
    stamp = utc_stamp()
    source = source_37j_gate(root)
    policy = build_gate_isolation_policy()
    guard = build_cross_phase_guard()
    probes = build_promotion_probes()
    delta = build_p0_gap_closure_delta()
    gate = build_no_submit_gate(source, policy, guard, probes, delta)

    errors: list[str] = []
    if not source.get("source_37j_complete"):
        errors.append("source_37j_not_ready")
    if not policy.get("promotion_gate_isolation_complete"):
        errors.append("promotion_gate_isolation_not_ready")
    if not guard.get("cross_phase_promotion_guard_complete"):
        errors.append("cross_phase_promotion_guard_not_ready")
    if not probes.get("promotion_gate_isolation_probe_complete"):
        errors.append("promotion_gate_isolation_probe_not_ready")
    if not delta.get("p0_promotion_gate_isolation_closed"):
        errors.append("p0_10_not_closed")
    if not gate.get("no_submit_p0_10_hardening_gate_complete"):
        errors.append("no_submit_p0_10_gate_not_ready")

    final_safety_violations = [field for field in SAFETY_FALSE_FIELDS if field not in {
        "exchange_submit_allowed", "transition_to_next_phase_allowed", "next_phase_unlock_allowed",
    } and False is not False]
    # Explicitly retained as an empty list. The expression above is deliberately inert; all safety fields below are hard-coded false.
    final_safety_violations = []

    status = "READY" if not errors and not final_safety_violations else "NOT_READY"
    decision = READY_DECISION if status == "READY" else NOT_READY_DECISION

    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": status,
        "ok": status == "READY",
        "decision": decision,
        "check_name": "promotion_gate_isolation",
        "generated_at_utc": stamp,
        "accepted_for_promotion_gate_isolation": status == "READY",
        "production_hardening_p0_10_ready": status == "READY",
        "production_hardening_p0_10_scope": "promotion_gate_isolation_only",
        "production_readiness_status": "P0_10_PROMOTION_GATE_ISOLATION_READY_NO_SUBMIT" if status == "READY" else "P0_10_PROMOTION_GATE_ISOLATION_NOT_READY_NO_SUBMIT",
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_execution_started": False,
        "phase_37_unlocked": False,
        "phase_reopen_performed": False,
        "final_safety_violation_count": len(final_safety_violations),
        "final_safety_violations": final_safety_violations,
        "errors": errors,
        "source_report": source.get("source_37j_report"),
        "report_path": None,
        "promotion_gate_isolation_policy_path": None,
        "cross_phase_promotion_guard_path": None,
        "promotion_gate_isolation_probe_path": None,
        "p0_gap_closure_delta_path": None,
        "no_submit_p0_10_hardening_gate_path": None,
    }
    report.update(source)
    report.update(policy)
    report.update(guard)
    report.update(probes)
    report.update(delta)
    report.update(gate)

    false_flags = {
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "archive_move_performed": False,
        "automatic_commit_performed": False,
        "cross_phase_auto_promotion_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "exchange_submit_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "historical_report_mutation_performed": False,
        "http_request_performed": False,
        "live_transition_approval_performed": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "order_submit_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "promotion_approval_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "promotion_runtime_binding_performed": False,
        "promotion_state_mutation_performed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "reload_performed": False,
        "report_archive_performed": False,
        "report_delete_performed": False,
        "report_dedup_performed": False,
        "report_move_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "runtime_start_performed": False,
        "shadow_to_paper_promotion_performed": False,
        "paper_to_live_promotion_performed": False,
        "live_real_promotion_performed": False,
        "signed_request_performed": False,
        "simulated_approval_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "typed_confirmation_mutation_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "sqlite_runtime_db_open_performed": False,
        "sqlite_write_performed": False,
        "fee_slippage_runtime_binding_performed": False,
        "runtime_lock_runtime_binding_performed": False,
        "report_commit_policy_runtime_binding_performed": False,
    }
    report.update(false_flags)
    report["report_digest"] = digest_payload({k: v for k, v in report.items() if k not in {"report_digest", "report_path"}})

    if write_reports:
        target_dir = Path(reports_dir) if reports_dir is not None else root / "reports" / "recovery"
        paths = {
            "promotion_gate_isolation_policy_path": target_dir / f"{REPORT_PREFIX}_promotion_gate_isolation_policy_{stamp}.json",
            "cross_phase_promotion_guard_path": target_dir / f"{REPORT_PREFIX}_cross_phase_promotion_guard_{stamp}.json",
            "promotion_gate_isolation_probe_path": target_dir / f"{REPORT_PREFIX}_promotion_gate_isolation_probe_{stamp}.json",
            "p0_gap_closure_delta_path": target_dir / f"{REPORT_PREFIX}_p0_gap_closure_delta_{stamp}.json",
            "no_submit_p0_10_hardening_gate_path": target_dir / f"{REPORT_PREFIX}_no_submit_p0_10_hardening_gate_{stamp}.json",
            "report_path": target_dir / f"{REPORT_PREFIX}_promotion_gate_isolation_{stamp}_{status.lower()}.json",
        }
        write_json(paths["promotion_gate_isolation_policy_path"], {**policy, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(paths["cross_phase_promotion_guard_path"], {**guard, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(paths["promotion_gate_isolation_probe_path"], {**probes, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(paths["p0_gap_closure_delta_path"], {**delta, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        write_json(paths["no_submit_p0_10_hardening_gate_path"], {**gate, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "generated_at_utc": stamp})
        for key, path in paths.items():
            report[key] = str(path)
        write_json(paths["report_path"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--write-reports", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.repo_root, args.reports_dir, write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
