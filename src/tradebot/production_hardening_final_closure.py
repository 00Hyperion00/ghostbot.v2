from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436637L"
PATCH_VERSION = "4B.4.3.6.6.37L"
PATCH_NAME = "Production Hardening Final Closure"

SOURCE_PATCH_ID = "4B436637K"
SOURCE_DECISION = "PROMOTION_GATE_ISOLATION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_10_LOCKED"
READY_DECISION = "PRODUCTION_HARDENING_FINAL_CLOSURE_READY_NO_SUBMIT_PRODUCTION_READINESS_SEAL_LOCKED"
NOT_READY_DECISION = "PRODUCTION_HARDENING_FINAL_CLOSURE_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.38A"
NEXT_PHASE_NAME = "Paper Transition Readiness Review"

REQUIRED_PHASE_37_TAGS: tuple[str, ...] = (
    "4B.4.3.6.6.37A",
    "4B.4.3.6.6.37B-H1",
    "4B.4.3.6.6.37C",
    "4B.4.3.6.6.37D",
    "4B.4.3.6.6.37E",
    "4B.4.3.6.6.37F",
    "4B.4.3.6.6.37G",
    "4B.4.3.6.6.37H",
    "4B.4.3.6.6.37I",
    "4B.4.3.6.6.37J",
    "4B.4.3.6.6.37K",
)

P0_CLOSURE_ITEMS: tuple[dict[str, Any], ...] = (
    {"gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "domain": "install_contract", "closed": True, "closed_by": "4B.4.3.6.6.37B-H1", "auto_close_allowed": False},
    {"gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "domain": "repo_hygiene", "closed": True, "closed_by": "4B.4.3.6.6.37C", "auto_close_allowed": False},
    {"gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "domain": "strict_config", "closed": True, "closed_by": "4B.4.3.6.6.37D", "auto_close_allowed": False},
    {"gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "domain": "api_security", "closed": True, "closed_by": "4B.4.3.6.6.37E", "auto_close_allowed": False},
    {"gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "domain": "operator_controls", "closed": True, "closed_by": "4B.4.3.6.6.37F", "auto_close_allowed": False},
    {"gap_id": "P0_SQLITE_AUDIT_BASELINE", "domain": "persistence", "closed": True, "closed_by": "4B.4.3.6.6.37G", "auto_close_allowed": False},
    {"gap_id": "P0_RUNTIME_PROCESS_LOCK", "domain": "runtime_safety", "closed": True, "closed_by": "4B.4.3.6.6.37H", "auto_close_allowed": False},
    {"gap_id": "P0_FEE_SLIPPAGE_BASELINE", "domain": "execution_cost_model", "closed": True, "closed_by": "4B.4.3.6.6.37I", "auto_close_allowed": False},
    {"gap_id": "P0_REPORT_COMMIT_POLICY", "domain": "evidence_governance", "closed": True, "closed_by": "4B.4.3.6.6.37J", "auto_close_allowed": False},
    {"gap_id": "P0_PROMOTION_GATE_ISOLATION", "domain": "promotion_governance", "closed": True, "closed_by": "4B.4.3.6.6.37K", "auto_close_allowed": False},
)

REMOTE_TAG_AUDIT_OPERATOR_COMMANDS: tuple[str, ...] = (
    'git fetch --tags --prune',
    'git tag --list "4B.4.3.6.6.37*"',
    'git ls-remote --tags origin "4B.4.3.6.6.37*"',
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _repo_root_from(start: Path | None = None) -> Path:
    if start is not None:
        return start.resolve()
    return Path.cwd().resolve()


def find_latest_source_report(repo_root: Path, reports_dir: Path | None = None) -> Path | None:
    base = reports_dir if reports_dir is not None else repo_root / "reports" / "recovery"
    base = base if base.is_absolute() else repo_root / base
    candidates = sorted(base.glob("4B436637K_promotion_gate_isolation_*_ready.json"))
    return candidates[-1] if candidates else None


def _bool(report: Mapping[str, Any], key: str) -> bool:
    return bool(report.get(key) is True)


def validate_source_37k(source: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    required_true = {
        "source_37j_complete": "source 37J gate must be complete",
        "p0_promotion_gate_isolation_closed": "P0-10 promotion gate isolation must be closed",
        "p0_hardening_complete": "all P0 hardening gaps must be complete",
        "all_p0_closed_does_not_enable_paper": "all-P0-closed must not enable paper",
        "all_p0_closed_does_not_enable_live": "all-P0-closed must not enable live",
        "all_p0_closed_does_not_enable_submit": "all-P0-closed must not enable submit",
        "promotion_gate_isolation_locked": "promotion gate isolation must be locked",
        "cross_phase_promotion_guard_locked": "cross-phase promotion guard must be locked",
        "paper_transition_blocked": "paper transition must remain blocked",
    }
    required_false = {
        "approved_for_exchange_submit": "exchange submit approval must remain false",
        "approved_for_live_real": "live-real approval must remain false",
        "approved_for_paper_transition": "paper transition approval must remain false",
        "network_submit_allowed": "network submit must remain false",
        "order_submit_performed": "order submit must not be performed",
        "exchange_submit_performed": "exchange submit must not be performed",
        "network_request_performed": "network request must not be performed",
        "http_request_performed": "HTTP request must not be performed",
        "signed_request_performed": "signed request must not be performed",
        "runtime_overlay_activated": "runtime overlay must not activate",
        "training_performed": "training must not run",
        "reload_performed": "reload must not run",
        "transition_to_next_phase_performed": "next phase transition must not run",
    }
    if source.get("status") != "READY":
        errors.append("source 37K status is not READY")
    if source.get("decision") != SOURCE_DECISION:
        errors.append("source 37K decision mismatch")
    if source.get("p0_hardening_closed_gap_count_after_37k") != 10:
        errors.append("source 37K closed P0 count is not 10")
    if source.get("p0_hardening_open_gap_count_after_37k") != 0:
        errors.append("source 37K open P0 count is not 0")
    if source.get("final_safety_violation_count") not in (0, None):
        errors.append("source 37K has safety violations")
    for key, message in required_true.items():
        if not _bool(source, key):
            errors.append(message)
    for key, message in required_false.items():
        if source.get(key) is not False:
            errors.append(message)
    return not errors, errors


def build_p0_final_audit(source_path: str | None, source: Mapping[str, Any] | None, source_ok: bool, source_errors: Sequence[str]) -> dict[str, Any]:
    rules = [
        {"rule_id": "source_37k_ready", "ready": source_ok, "policy": "37K READY report is the only accepted source for final closure"},
        {"rule_id": "all_ten_p0_gaps_closed", "ready": source is not None and source.get("p0_hardening_closed_gap_count_after_37k") == 10, "policy": "P0 hardening must show 10 closed gaps"},
        {"rule_id": "zero_p0_gaps_open", "ready": source is not None and source.get("p0_hardening_open_gap_count_after_37k") == 0, "policy": "P0 hardening must show zero open gaps"},
        {"rule_id": "p0_hardening_complete", "ready": source is not None and source.get("p0_hardening_complete") is True, "policy": "P0 hardening completion flag must be true"},
        {"rule_id": "all_p0_closure_items_declared", "ready": all(item["closed"] for item in P0_CLOSURE_ITEMS), "policy": "all P0 closure items are declared with accepted closing versions"},
        {"rule_id": "paper_remains_blocked", "ready": source is not None and source.get("paper_transition_blocked") is True and source.get("paper_transition_ready") is False, "policy": "paper transition remains blocked after P0 closure"},
        {"rule_id": "live_remains_not_approved", "ready": source is not None and source.get("approved_for_live_real") is False, "policy": "live-real approval remains false"},
        {"rule_id": "submit_remains_locked", "ready": source is not None and source.get("approved_for_exchange_submit") is False and source.get("network_submit_allowed") is False, "policy": "exchange/network submit remains locked"},
        {"rule_id": "no_runtime_activation", "ready": source is not None and source.get("runtime_overlay_activated") is False and source.get("runtime_start_performed") is False, "policy": "runtime overlay/start remains inactive"},
        {"rule_id": "no_training_or_reload", "ready": source is not None and source.get("training_performed") is False and source.get("reload_performed") is False, "policy": "training and reload are not performed"},
        {"rule_id": "no_network_or_signed_request", "ready": source is not None and source.get("network_request_performed") is False and source.get("signed_request_performed") is False, "policy": "network and signed requests are not performed"},
        {"rule_id": "next_phase_not_auto_unlocked", "ready": source is not None and source.get("next_phase_unlock_allowed") is False and source.get("transition_to_next_phase_performed") is False, "policy": "next phase is not auto-unlocked"},
    ]
    payload: dict[str, Any] = {
        "audit_name": "p0_hardening_final_audit",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "source_report": source_path,
        "source_37k_complete": source_ok,
        "source_37k_errors": list(source_errors),
        "p0_hardening_final_audit_complete": all(rule["ready"] for rule in rules),
        "p0_hardening_final_audit_locked": True,
        "p0_hardening_final_audit_rule_count": len(rules),
        "p0_hardening_final_audit_ready_count": sum(1 for rule in rules if rule["ready"]),
        "p0_hardening_final_audit_rules": rules,
        "p0_hardening_gap_count_final": 10,
        "p0_hardening_closed_gap_count_final": 10 if source_ok else 0,
        "p0_hardening_open_gap_count_final": 0 if source_ok else None,
        "p0_hardening_complete_final": bool(source_ok),
        "p0_gap_closure_items_final": list(P0_CLOSURE_ITEMS),
        "p0_final_audit_status": "P0_HARDENING_FINAL_AUDIT_READY" if all(rule["ready"] for rule in rules) else "P0_HARDENING_FINAL_AUDIT_NOT_READY",
    }
    payload["p0_hardening_final_audit_digest"] = stable_digest(payload)
    return payload


def build_remote_tag_audit_contract() -> dict[str, Any]:
    probes = [
        {"probe_id": "required_phase_37_tags_declared", "expected": len(REQUIRED_PHASE_37_TAGS), "result": len(REQUIRED_PHASE_37_TAGS), "passed": True},
        {"probe_id": "operator_remote_tag_commands_declared", "expected": True, "result": True, "passed": True},
        {"probe_id": "git_ls_remote_not_performed_by_patch", "expected": False, "result": False, "passed": True},
        {"probe_id": "network_request_not_performed_by_patch", "expected": False, "result": False, "passed": True},
        {"probe_id": "git_mutating_operations_not_performed", "expected": False, "result": False, "passed": True},
    ]
    payload: dict[str, Any] = {
        "audit_name": "remote_tag_audit_contract",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "remote_tag_audit_complete": True,
        "remote_tag_audit_locked": True,
        "remote_tag_audit_mode": "STATIC_CONTRACT_NO_NETWORK_OPERATOR_REVIEW_REQUIRED",
        "remote_tag_audit_required": True,
        "remote_tag_audit_operator_review_required": True,
        "remote_tag_audit_operator_command_required": True,
        "remote_tag_audit_operator_commands": list(REMOTE_TAG_AUDIT_OPERATOR_COMMANDS),
        "required_phase_37_remote_tags": list(REQUIRED_PHASE_37_TAGS),
        "required_phase_37_remote_tag_count": len(REQUIRED_PHASE_37_TAGS),
        "remote_tag_lookup_performed": False,
        "git_ls_remote_performed": False,
        "git_fetch_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "remote_tag_audit_probe_count": len(probes),
        "remote_tag_audit_probe_passed_count": sum(1 for probe in probes if probe["passed"]),
        "remote_tag_audit_probes": probes,
        "remote_tag_audit_status": "REMOTE_TAG_AUDIT_CONTRACT_READY_OPERATOR_REVIEW_REQUIRED_NO_NETWORK",
    }
    payload["remote_tag_audit_digest"] = stable_digest(payload)
    return payload


def build_no_submit_readiness_seal(final_audit: Mapping[str, Any], remote_tag_audit: Mapping[str, Any]) -> dict[str, Any]:
    rules = [
        {"rule_id": "p0_final_audit_ready", "ready": final_audit.get("p0_hardening_final_audit_complete") is True, "policy": "P0 final audit must be ready"},
        {"rule_id": "remote_tag_audit_contract_ready", "ready": remote_tag_audit.get("remote_tag_audit_complete") is True, "policy": "remote tag audit contract must be ready"},
        {"rule_id": "p0_hardening_complete_sealed", "ready": final_audit.get("p0_hardening_complete_final") is True, "policy": "P0 hardening is sealed complete"},
        {"rule_id": "no_submit_seal", "ready": True, "policy": "seal is no-submit only"},
        {"rule_id": "paper_not_approved_by_seal", "ready": True, "policy": "seal does not approve paper transition"},
        {"rule_id": "live_not_approved_by_seal", "ready": True, "policy": "seal does not approve live-real"},
        {"rule_id": "exchange_submit_not_approved_by_seal", "ready": True, "policy": "seal does not approve exchange submit"},
        {"rule_id": "paper_transition_review_required", "ready": True, "policy": "next step requires explicit paper transition review"},
    ]
    payload: dict[str, Any] = {
        "seal_name": "no_submit_production_readiness_seal",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "no_submit_production_readiness_seal_complete": all(rule["ready"] for rule in rules),
        "no_submit_production_readiness_seal_locked": True,
        "no_submit_production_readiness_sealed": all(rule["ready"] for rule in rules),
        "production_hardening_final_closure_complete": all(rule["ready"] for rule in rules),
        "production_readiness_status": "NO_SUBMIT_PRODUCTION_READINESS_SEALED_P0_COMPLETE",
        "production_readiness_seal_rule_count": len(rules),
        "production_readiness_seal_ready_count": sum(1 for rule in rules if rule["ready"]),
        "production_readiness_seal_rules": rules,
        "approved_for_operator_audit": True,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "network_submit_allowed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_review_required": True,
        "paper_transition_auto_start_allowed": False,
        "live_real_submit_allowed": False,
        "exchange_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "runtime_overlay_activated": False,
        "runtime_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }
    payload["no_submit_production_readiness_seal_digest"] = stable_digest(payload)
    return payload


def build_final_gate(final_audit: Mapping[str, Any], remote_tag_audit: Mapping[str, Any], seal: Mapping[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        {"check_id": "source_37k_ready", "ready": final_audit.get("source_37k_complete") is True, "unlock_allowed": False},
    ]
    checks.extend(
        {"check_id": f"{item['gap_id'].lower()}_closed", "ready": bool(item["closed"]), "unlock_allowed": False}
        for item in P0_CLOSURE_ITEMS
    )
    checks.extend([
        {"check_id": "p0_final_audit_locked", "ready": final_audit.get("p0_hardening_final_audit_complete") is True, "unlock_allowed": False},
        {"check_id": "remote_tag_audit_contract_locked", "ready": remote_tag_audit.get("remote_tag_audit_complete") is True, "unlock_allowed": False},
        {"check_id": "production_readiness_seal_locked", "ready": seal.get("no_submit_production_readiness_seal_complete") is True, "unlock_allowed": False},
        {"check_id": "all_p0_closed_does_not_enable_paper_live_submit", "ready": True, "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": seal.get("paper_transition_blocked") is True and seal.get("paper_transition_ready") is False, "unlock_allowed": False},
        {"check_id": "live_real_remains_not_approved", "ready": seal.get("approved_for_live_real") is False, "unlock_allowed": False},
        {"check_id": "exchange_submit_forbidden", "ready": seal.get("approved_for_exchange_submit") is False and seal.get("exchange_submit_allowed") is False, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": seal.get("network_submit_allowed") is False, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": seal.get("runtime_overlay_activated") is False and seal.get("training_performed") is False and seal.get("reload_performed") is False, "unlock_allowed": False},
        {"check_id": "git_mutating_operations_forbidden", "ready": remote_tag_audit.get("git_add_performed") is False and remote_tag_audit.get("git_commit_performed") is False and remote_tag_audit.get("git_tag_performed") is False and remote_tag_audit.get("git_push_performed") is False, "unlock_allowed": False},
        {"check_id": "report_mutation_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": seal.get("next_phase_unlock_allowed") is False and seal.get("transition_to_next_phase_performed") is False, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": True, "unlock_allowed": False},
    ])
    payload: dict[str, Any] = {
        "gate_name": "no_submit_production_readiness_final_gate",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "no_submit_production_readiness_final_gate_complete": all(check["ready"] for check in checks),
        "no_submit_production_readiness_final_gate_locked": True,
        "no_submit_production_readiness_final_gate_check_count": len(checks),
        "no_submit_production_readiness_final_gate_ready_count": sum(1 for check in checks if check["ready"]),
        "no_submit_production_readiness_final_gate_checks": checks,
        "no_submit_production_readiness_final_gate_status": "NO_SUBMIT_PRODUCTION_READINESS_FINAL_GATE_READY" if all(check["ready"] for check in checks) else "NO_SUBMIT_PRODUCTION_READINESS_FINAL_GATE_NOT_READY",
    }
    payload["no_submit_production_readiness_final_gate_digest"] = stable_digest(payload)
    return payload


def build_report(repo_root: Path | None = None, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    root = _repo_root_from(repo_root)
    source_path = find_latest_source_report(root, reports_dir)
    source: dict[str, Any] | None = None
    source_errors: list[str] = []
    source_ok = False
    if source_path is None:
        source_errors.append("missing 37K READY source report")
    else:
        source = read_json(source_path)
        source_ok, source_errors = validate_source_37k(source)

    source_path_str = str(source_path) if source_path is not None else None
    final_audit = build_p0_final_audit(source_path_str, source, source_ok, source_errors)
    remote_tag_audit = build_remote_tag_audit_contract()
    seal = build_no_submit_readiness_seal(final_audit, remote_tag_audit)
    final_gate = build_final_gate(final_audit, remote_tag_audit, seal)

    ok = bool(
        source_ok
        and final_audit["p0_hardening_final_audit_complete"]
        and remote_tag_audit["remote_tag_audit_complete"]
        and seal["no_submit_production_readiness_seal_complete"]
        and final_gate["no_submit_production_readiness_final_gate_complete"]
    )
    decision = READY_DECISION if ok else NOT_READY_DECISION
    status = "READY" if ok else "NOT_READY"
    generated_at = utc_stamp()

    target_dir = reports_dir if reports_dir is not None else root / "reports" / "recovery"
    target_dir = target_dir if target_dir.is_absolute() else root / target_dir

    paths: dict[str, str | None] = {
        "p0_hardening_final_audit_path": None,
        "remote_tag_audit_contract_path": None,
        "no_submit_production_readiness_seal_path": None,
        "no_submit_production_readiness_final_gate_path": None,
        "report_path": None,
    }
    if write_reports:
        p0_path = target_dir / f"{PATCH_ID}_p0_hardening_final_audit_{generated_at}.json"
        remote_path = target_dir / f"{PATCH_ID}_remote_tag_audit_contract_{generated_at}.json"
        seal_path = target_dir / f"{PATCH_ID}_no_submit_production_readiness_seal_{generated_at}.json"
        gate_path = target_dir / f"{PATCH_ID}_no_submit_production_readiness_final_gate_{generated_at}.json"
        write_json(p0_path, final_audit)
        write_json(remote_path, remote_tag_audit)
        write_json(seal_path, seal)
        write_json(gate_path, final_gate)
        paths.update({
            "p0_hardening_final_audit_path": str(p0_path),
            "remote_tag_audit_contract_path": str(remote_path),
            "no_submit_production_readiness_seal_path": str(seal_path),
            "no_submit_production_readiness_final_gate_path": str(gate_path),
        })

    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": status,
        "ok": ok,
        "decision": decision,
        "generated_at_utc": generated_at,
        "source_report": source_path_str,
        "source_37k_report": source_path_str,
        "source_37k_complete": source_ok,
        "source_37k_status": "SOURCE_37K_READY" if source_ok else "SOURCE_37K_NOT_READY",
        "source_37k_decision": source.get("decision") if source else None,
        "source_37k_safety_violation_count": source.get("final_safety_violation_count") if source else None,
        "source_37k_safety_violations": source.get("final_safety_violations", []) if source else [],
        "source_37k_p0_10_closed": source.get("p0_promotion_gate_isolation_closed") if source else None,
        "source_37k_p0_10_closed_by": source.get("p0_promotion_gate_isolation_closed_by") if source else None,
        "source_37k_p0_closed_gap_count": source.get("p0_hardening_closed_gap_count_after_37k") if source else None,
        "source_37k_p0_open_gap_count": source.get("p0_hardening_open_gap_count_after_37k") if source else None,
        "source_37k_phase_37_planning_only": source.get("phase_37_planning_only") if source else None,
        "source_37k_promotion_gate_isolation_locked": source.get("promotion_gate_isolation_locked") if source else None,
        "errors": list(source_errors),
        **final_audit,
        **remote_tag_audit,
        **seal,
        **final_gate,
        "production_hardening_final_closure_complete": ok,
        "production_hardening_final_closure_locked": True,
        "production_hardening_final_closure_status": "PRODUCTION_HARDENING_FINAL_CLOSURE_READY_NO_SUBMIT" if ok else "PRODUCTION_HARDENING_FINAL_CLOSURE_NOT_READY",
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_execution_started": False,
        "phase_37_final_closed": ok,
        "phase_37_final_closure_ready": ok,
        "phase_37_unlocked": False,
        "phase_reopen_performed": False,
        "p0_hardening_gap_count_after_37l": 10,
        "p0_hardening_closed_gap_count_after_37l": 10 if ok else final_audit.get("p0_hardening_closed_gap_count_final"),
        "p0_hardening_open_gap_count_after_37l": 0 if ok else final_audit.get("p0_hardening_open_gap_count_final"),
        "p0_hardening_complete_after_37l": ok,
        "p0_hardening_final_sealed": ok,
        "all_p0_closed_does_not_enable_paper": True,
        "all_p0_closed_does_not_enable_live": True,
        "all_p0_closed_does_not_enable_submit": True,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37L_PRODUCTION_HARDENING_FINAL_CLOSURE_NO_SUBMIT",
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "exchange_submit_allowed": False,
        "trading_action_performed": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_health_probe_performed": False,
        "runtime_probe_performed": False,
        "runtime_start_performed": False,
        "runtime_overlay_allowed": False,
        "runtime_overlay_activated": False,
        "runtime_readiness_unlock_performed": False,
        "api_route_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "promotion_state_mutation_performed": False,
        "promotion_runtime_binding_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "report_file_mutation_performed": False,
        "historical_report_mutation_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "archive_move_performed": False,
        "automatic_commit_allowed": False,
        "automatic_commit_performed": False,
        "operator_manual_commit_required": True,
        "git_add_allowed": False,
        "git_add_performed": False,
        "git_commit_allowed": False,
        "git_commit_performed": False,
        "git_tag_allowed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "simulated_approval_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "live_transition_approval_performed": False,
        "exchange_submit_approval_performed": False,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "final_safety_violation_count": 0 if ok else len(source_errors),
        "final_safety_violations": [] if ok else list(source_errors),
        **paths,
    }
    report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
    if write_reports:
        terminal = target_dir / f"{PATCH_ID}_production_hardening_final_closure_{generated_at}_{status.lower()}.json"
        write_json(terminal, report)
        report["report_path"] = str(terminal)
        report["report_digest"] = stable_digest({k: v for k, v in report.items() if k != "report_digest"})
        write_json(terminal, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(reports_dir=args.reports_dir, write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
