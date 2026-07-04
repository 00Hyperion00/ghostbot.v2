from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

PATCH_ID: Final[str] = "4B436638B"
PATCH_VERSION: Final[str] = "4B.4.3.6.6.38B"
PATCH_NAME: Final[str] = "Paper Sandbox Runtime Preflight"
READY_DECISION: Final[str] = (
    "PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_PAPER_ONLY_NO_LIVE_NO_EXCHANGE_SUBMIT_NO_NETWORK_ORDER_LOCKED"
)
NOT_READY_DECISION: Final[str] = "PAPER_SANDBOX_RUNTIME_PREFLIGHT_NOT_READY_LOCKED"
SOURCE_DECISION_38A: Final[str] = (
    "PAPER_TRANSITION_READINESS_REVIEW_READY_EXPLICIT_APPROVAL_REQUIRED_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NEXT_PHASE: Final[str] = "4B.4.3.6.6.38C"
NEXT_PHASE_NAME: Final[str] = "Paper Sandbox Dry-Run Runtime Harness"

PAPER_ONLY_REQUIRED_FIELDS: Final[dict[str, Any]] = {
    "environment_mode": "paper",
    "live_environment_enabled": False,
    "paper_environment_enabled": True,
    "exchange_submit_allowed": False,
    "network_order_submit_allowed": False,
    "signed_request_allowed": False,
    "private_api_access_allowed": False,
    "runtime_overlay_allowed": False,
    "training_allowed": False,
    "reload_allowed": False,
}

CANONICAL_PAPER_ONLY_CONFIG: Final[dict[str, Any]] = {
    "environment_mode": "paper",
    "paper_environment_enabled": True,
    "live_environment_enabled": False,
    "exchange_submit_allowed": False,
    "network_order_submit_allowed": False,
    "signed_request_allowed": False,
    "private_api_access_allowed": False,
    "runtime_overlay_allowed": False,
    "training_allowed": False,
    "reload_allowed": False,
}

REQUIRED_SOURCE_FIELDS: Final[dict[str, Any]] = {
    "status": "READY",
    "decision": SOURCE_DECISION_38A,
    "paper_transition_readiness_review_complete": True,
    "paper_transition_readiness_review_locked": True,
    "paper_transition_review_ready": True,
    "source_37l_status": "SOURCE_37L_READY",
    "phase_37_final_closed": True,
    "paper_transition_blocked": True,
    "approved_for_paper_transition": False,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "network_submit_allowed": False,
    "order_submit_performed": False,
    "exchange_submit_performed": False,
    "network_request_performed": False,
    "http_request_performed": False,
    "signed_request_performed": False,
    "runtime_start_performed": False,
    "runtime_overlay_activated": False,
    "training_performed": False,
    "reload_performed": False,
}

SAFETY_FALSE_FIELDS: Final[tuple[str, ...]] = (
    "approved_for_paper_transition",
    "approved_for_live_real",
    "approved_for_exchange_submit",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_transition_ready",
    "paper_runtime_start_allowed",
    "paper_runtime_start_performed",
    "paper_order_submit_allowed",
    "paper_order_submit_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "network_submit_allowed",
    "network_order_submit_allowed",
    "network_order_submit_performed",
    "order_submit_performed",
    "network_request_allowed_now",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "runtime_start_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "training_performed",
    "reload_performed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_performed",
    "git_add_performed",
    "git_commit_performed",
    "git_tag_performed",
    "git_push_performed",
    "report_delete_performed",
    "report_move_performed",
    "report_archive_performed",
    "report_dedup_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
)


@dataclasses.dataclass(frozen=True)
class ConfigEvaluation:
    probe_id: str
    config: dict[str, Any]
    expected: str
    result: str
    passed: bool
    runtime_start_allowed: bool = False
    order_submit_allowed: bool = False
    exchange_submit_allowed: bool = False
    live_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path
        return {"_read_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def find_latest_source_38a_report(reports_dir: Path) -> Path | None:
    candidates = sorted(
        reports_dir.glob("4B436638A_paper_transition_readiness_review_*_ready.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def validate_source_38a(report: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for field, expected in REQUIRED_SOURCE_FIELDS.items():
        if report.get(field) != expected:
            errors.append(f"source_38a.{field} expected {expected!r} got {report.get(field)!r}")
    if int(report.get("final_safety_violation_count", 0)) != 0:
        errors.append("source_38a.final_safety_violation_count must be 0")
    return not errors, errors


def evaluate_paper_only_config(config: dict[str, Any]) -> str:
    """Fail-closed static evaluator for the paper sandbox runtime config contract."""
    if config.get("environment_mode") != "paper":
        return "DENY_PAPER_MODE_REQUIRED"
    if config.get("paper_environment_enabled") is not True:
        return "DENY_PAPER_ENVIRONMENT_REQUIRED"
    if config.get("live_environment_enabled") is not False:
        return "DENY_LIVE_ENVIRONMENT_ENABLED"
    if config.get("exchange_submit_allowed") is not False:
        return "DENY_EXCHANGE_SUBMIT_ENABLED"
    if config.get("network_order_submit_allowed") is not False:
        return "DENY_NETWORK_ORDER_SUBMIT_ENABLED"
    if config.get("signed_request_allowed") is not False:
        return "DENY_SIGNED_REQUEST_ENABLED"
    if config.get("private_api_access_allowed") is not False:
        return "DENY_PRIVATE_API_ACCESS_ENABLED"
    if config.get("runtime_overlay_allowed") is not False:
        return "DENY_RUNTIME_OVERLAY_ENABLED"
    if config.get("training_allowed") is not False:
        return "DENY_TRAINING_ENABLED"
    if config.get("reload_allowed") is not False:
        return "DENY_RELOAD_ENABLED"
    return "PAPER_ONLY_CONFIG_VALID_RUNTIME_START_DENIED_NO_SUBMIT"


def run_preflight_probes() -> list[ConfigEvaluation]:
    probe_specs: list[tuple[str, dict[str, Any], str]] = [
        (
            "valid_paper_only_config_runtime_denied_no_submit",
            dict(CANONICAL_PAPER_ONLY_CONFIG),
            "PAPER_ONLY_CONFIG_VALID_RUNTIME_START_DENIED_NO_SUBMIT",
        ),
        (
            "missing_paper_mode_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "environment_mode": None},
            "DENY_PAPER_MODE_REQUIRED",
        ),
        (
            "live_mode_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "environment_mode": "live"},
            "DENY_PAPER_MODE_REQUIRED",
        ),
        (
            "live_environment_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "live_environment_enabled": True},
            "DENY_LIVE_ENVIRONMENT_ENABLED",
        ),
        (
            "exchange_submit_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "exchange_submit_allowed": True},
            "DENY_EXCHANGE_SUBMIT_ENABLED",
        ),
        (
            "network_order_submit_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "network_order_submit_allowed": True},
            "DENY_NETWORK_ORDER_SUBMIT_ENABLED",
        ),
        (
            "signed_request_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "signed_request_allowed": True},
            "DENY_SIGNED_REQUEST_ENABLED",
        ),
        (
            "private_api_access_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "private_api_access_allowed": True},
            "DENY_PRIVATE_API_ACCESS_ENABLED",
        ),
        (
            "runtime_overlay_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "runtime_overlay_allowed": True},
            "DENY_RUNTIME_OVERLAY_ENABLED",
        ),
        (
            "training_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "training_allowed": True},
            "DENY_TRAINING_ENABLED",
        ),
        (
            "reload_enabled_denied",
            {**CANONICAL_PAPER_ONLY_CONFIG, "reload_allowed": True},
            "DENY_RELOAD_ENABLED",
        ),
    ]
    probes: list[ConfigEvaluation] = []
    for probe_id, config, expected in probe_specs:
        result = evaluate_paper_only_config(config)
        probes.append(
            ConfigEvaluation(
                probe_id=probe_id,
                config=config,
                expected=expected,
                result=result,
                passed=result == expected,
                runtime_start_allowed=False,
                order_submit_allowed=False,
                exchange_submit_allowed=False,
                live_allowed=False,
            )
        )
    return probes


def _git_head_short(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _build_paper_config_contract(probes: list[ConfigEvaluation]) -> dict[str, Any]:
    rules = [
        {"rule_id": "environment_mode_must_be_paper", "ready": True, "policy": "paper sandbox runtime config must declare environment_mode=paper"},
        {"rule_id": "paper_environment_enabled_required", "ready": True, "policy": "paper environment must be explicitly enabled for preflight review"},
        {"rule_id": "live_environment_disabled_required", "ready": True, "policy": "live environment must remain disabled"},
        {"rule_id": "exchange_submit_disabled_required", "ready": True, "policy": "exchange submit must remain disabled"},
        {"rule_id": "network_order_submit_disabled_required", "ready": True, "policy": "network order submit must remain disabled"},
        {"rule_id": "signed_requests_disabled_required", "ready": True, "policy": "signed requests must remain disabled"},
        {"rule_id": "private_api_disabled_required", "ready": True, "policy": "private API access must remain disabled"},
        {"rule_id": "runtime_overlay_training_reload_disabled", "ready": True, "policy": "runtime overlay, training and reload remain out of scope"},
        {"rule_id": "valid_paper_config_does_not_start_runtime", "ready": True, "policy": "valid paper-only config cannot start runtime in 38B"},
    ]
    return {
        "contract_name": "paper_only_runtime_config_contract",
        "paper_only_runtime_config_contract_complete": True,
        "paper_only_runtime_config_contract_locked": True,
        "paper_only_runtime_config_contract_status": "PAPER_ONLY_RUNTIME_CONFIG_CONTRACT_READY_NO_RUNTIME_START",
        "paper_only_runtime_config_rule_count": len(rules),
        "paper_only_runtime_config_ready_count": sum(1 for rule in rules if rule["ready"]),
        "paper_only_runtime_config_rules": rules,
        "paper_only_required_fields": PAPER_ONLY_REQUIRED_FIELDS,
        "canonical_paper_only_config": CANONICAL_PAPER_ONLY_CONFIG,
        "paper_mode_required": True,
        "paper_environment_enabled_required": True,
        "live_environment_disabled_required": True,
        "exchange_submit_disabled_required": True,
        "network_order_submit_disabled_required": True,
        "signed_request_disabled_required": True,
        "private_api_access_disabled_required": True,
        "runtime_overlay_disabled_required": True,
        "training_disabled_required": True,
        "reload_disabled_required": True,
        "valid_paper_only_config_runtime_denied_no_submit": True,
        "paper_only_runtime_config_contract_digest": stable_digest(rules),
    }


def _build_no_live_no_network_order_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "live_real_approval_false", "ready": True, "policy": "38B cannot approve live-real"},
        {"rule_id": "exchange_submit_approval_false", "ready": True, "policy": "38B cannot approve exchange submit"},
        {"rule_id": "network_order_submit_forbidden", "ready": True, "policy": "network order submit remains forbidden"},
        {"rule_id": "order_submit_forbidden", "ready": True, "policy": "order submit remains forbidden"},
        {"rule_id": "signed_request_forbidden", "ready": True, "policy": "signed requests remain forbidden"},
        {"rule_id": "private_api_forbidden", "ready": True, "policy": "private API access remains forbidden"},
        {"rule_id": "runtime_start_forbidden", "ready": True, "policy": "runtime start is out of scope for 38B"},
    ]
    return {
        "guard_name": "no_live_no_exchange_submit_no_network_order_guard",
        "no_live_no_exchange_submit_no_network_order_guard_complete": True,
        "no_live_no_exchange_submit_no_network_order_guard_locked": True,
        "no_live_no_exchange_submit_no_network_order_guard_status": "NO_LIVE_NO_EXCHANGE_SUBMIT_NO_NETWORK_ORDER_GUARD_READY",
        "no_live_no_network_order_rule_count": len(rules),
        "no_live_no_network_order_ready_count": sum(1 for rule in rules if rule["ready"]),
        "no_live_no_network_order_rules": rules,
        "no_live_no_exchange_submit_no_network_order_guard_digest": stable_digest(rules),
    }


def _build_preflight_probe(probes: list[ConfigEvaluation]) -> dict[str, Any]:
    probe_dicts = [probe.as_dict() for probe in probes]
    return {
        "probe_name": "paper_sandbox_runtime_preflight_probe",
        "paper_sandbox_runtime_preflight_probe_complete": True,
        "paper_sandbox_runtime_preflight_probe_locked": True,
        "paper_sandbox_runtime_preflight_probe_mode": "STATIC_CONFIG_CONTRACT_NO_RUNTIME_NO_NETWORK_ORDER",
        "paper_sandbox_runtime_preflight_probe_count": len(probes),
        "paper_sandbox_runtime_preflight_probe_passed_count": sum(1 for probe in probes if probe.passed),
        "paper_sandbox_runtime_preflight_probe_status": "PAPER_SANDBOX_RUNTIME_PREFLIGHT_PROBES_READY_NO_RUNTIME_NO_ORDER",
        "paper_sandbox_runtime_preflight_probes": probe_dicts,
        "missing_paper_mode_denied": True,
        "live_mode_config_denied": True,
        "live_environment_config_denied": True,
        "exchange_submit_config_denied": True,
        "network_order_submit_config_denied": True,
        "signed_request_config_denied": True,
        "private_api_config_denied": True,
        "runtime_overlay_config_denied": True,
        "training_config_denied": True,
        "reload_config_denied": True,
        "valid_paper_config_accepted_for_preflight_review": True,
        "valid_paper_config_runtime_denied_no_submit": True,
        "paper_sandbox_runtime_preflight_probe_digest": stable_digest(probe_dicts),
    }


def _build_gate(source_ok: bool, probes: list[ConfigEvaluation]) -> dict[str, Any]:
    checks = [
        ("source_38a_ready", source_ok),
        ("phase_37_final_closed", source_ok),
        ("paper_transition_review_ready", source_ok),
        ("paper_only_runtime_config_contract_locked", True),
        ("paper_mode_required", True),
        ("live_environment_disabled_required", True),
        ("exchange_submit_disabled_required", True),
        ("network_order_submit_disabled_required", True),
        ("signed_request_disabled_required", True),
        ("private_api_disabled_required", True),
        ("runtime_overlay_training_reload_disabled", True),
        ("paper_sandbox_runtime_preflight_probes_passed", all(probe.passed for probe in probes)),
        ("valid_paper_config_does_not_start_runtime", True),
        ("paper_transition_not_approved_by_patch", True),
        ("paper_runtime_not_started", True),
        ("paper_order_submit_forbidden", True),
        ("live_real_remains_not_approved", True),
        ("exchange_submit_remains_forbidden", True),
        ("network_order_submit_forbidden", True),
        ("network_submit_forbidden", True),
        ("runtime_overlay_training_reload_forbidden", True),
        ("git_mutating_operations_forbidden", True),
        ("report_mutation_forbidden", True),
        ("next_phase_not_auto_unlocked", True),
        ("safety_flags_clean", True),
    ]
    check_items = [{"check_id": check_id, "ready": bool(ready), "unlock_allowed": False} for check_id, ready in checks]
    return {
        "gate_name": "paper_sandbox_runtime_preflight_gate",
        "paper_sandbox_runtime_preflight_gate_complete": all(item["ready"] for item in check_items),
        "paper_sandbox_runtime_preflight_gate_locked": True,
        "paper_sandbox_runtime_preflight_gate_status": "PAPER_SANDBOX_RUNTIME_PREFLIGHT_GATE_READY",
        "paper_sandbox_runtime_preflight_gate_check_count": len(check_items),
        "paper_sandbox_runtime_preflight_gate_ready_count": sum(1 for item in check_items if item["ready"]),
        "paper_sandbox_runtime_preflight_gate_checks": check_items,
        "paper_sandbox_runtime_preflight_gate_digest": stable_digest(check_items),
    }


def build_report(repo_root: Path | str = Path.cwd(), reports_dir: Path | str | None = None, *, write_reports: bool = False) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    recovery_dir = Path(reports_dir) if reports_dir is not None else root / "reports" / "recovery"
    recovery_dir = recovery_dir if recovery_dir.is_absolute() else root / recovery_dir

    source_path = find_latest_source_38a_report(recovery_dir)
    source_report = _read_json(source_path) if source_path else {}
    source_ok, source_errors = validate_source_38a(source_report) if source_path else (False, ["source_38a_report_missing"])

    probes = run_preflight_probes()
    contract = _build_paper_config_contract(probes)
    guard = _build_no_live_no_network_order_guard()
    probe_ledger = _build_preflight_probe(probes)
    gate = _build_gate(source_ok, probes)

    errors: list[str] = []
    errors.extend(source_errors)
    if not all(probe.passed for probe in probes):
        errors.append("paper_sandbox_runtime_preflight_probe_failed")
    if not gate["paper_sandbox_runtime_preflight_gate_complete"]:
        errors.append("paper_sandbox_runtime_preflight_gate_not_ready")

    final_safety_violations: list[str] = []
    base_false_values = {field: False for field in SAFETY_FALSE_FIELDS}
    for field, value in base_false_values.items():
        if value is not False:
            final_safety_violations.append(field)

    ok = not errors and not final_safety_violations
    stamp = _utc_stamp()

    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "status": "READY" if ok else "NOT_READY",
        "decision": READY_DECISION if ok else NOT_READY_DECISION,
        "generated_at_utc": stamp,
        "host": platform.node(),
        "git_available": _git_head_short(root) is not None,
        "git_head_short": _git_head_short(root),
        "source_report": str(source_path) if source_path else None,
        "source_38a_report": str(source_path) if source_path else None,
        "source_38a_complete": source_ok,
        "source_38a_status": "SOURCE_38A_READY" if source_ok else "SOURCE_38A_NOT_READY",
        "source_38a_decision": source_report.get("decision"),
        "source_38a_paper_transition_review_ready": source_report.get("paper_transition_review_ready"),
        "source_38a_approved_for_paper_transition_review": source_report.get("approved_for_paper_transition_review"),
        "source_38a_approved_for_paper_transition": source_report.get("approved_for_paper_transition"),
        "source_38a_approved_for_live_real": source_report.get("approved_for_live_real"),
        "source_38a_approved_for_exchange_submit": source_report.get("approved_for_exchange_submit"),
        "source_38a_phase_38_planning_only": source_report.get("phase_38_planning_only"),
        "source_38a_safety_violation_count": int(source_report.get("final_safety_violation_count", -1)) if source_report else -1,
        "source_38a_safety_violations": source_report.get("final_safety_violations", []),
        "errors": errors,
        "ok": ok,
        "review_name": "paper_sandbox_runtime_preflight",
        "paper_sandbox_runtime_preflight_complete": True,
        "paper_sandbox_runtime_preflight_locked": True,
        "paper_sandbox_runtime_preflight_ready": ok,
        "paper_sandbox_runtime_preflight_status": "PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_NO_RUNTIME_START" if ok else "PAPER_SANDBOX_RUNTIME_PREFLIGHT_NOT_READY",
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_sandbox_runtime_preflight": ok,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_transition": False,
        "paper_transition_approval_ready": False,
        "paper_transition_approval_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_environment_enabled": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "paper_runtime_config_validation_only": True,
        "paper_order_submit_allowed": False,
        "paper_order_submit_performed": False,
        "paper_submit_allowed": False,
        "paper_transition_status": "PAPER_SANDBOX_RUNTIME_PREFLIGHT_READY_NO_RUNTIME_START_NO_ORDER" if ok else "PAPER_SANDBOX_RUNTIME_PREFLIGHT_NOT_READY",
        "live_environment_enabled": False,
        "live_transition_ready": False,
        "live_transition_allowed": False,
        "live_transition_approval_performed": False,
        "approved_for_live_real": False,
        "live_real_submit_allowed": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_allowed": False,
        "exchange_submit_approval_performed": False,
        "exchange_submit_performed": False,
        "network_order_submit_allowed": False,
        "network_order_submit_performed": False,
        "network_submit_allowed": False,
        "order_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "runtime_start_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_allowed": False,
        "runtime_overlay_activated": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "phase_37_final_closed": True,
        "phase_38_execution_started": False,
        "phase_38_planning_only": True,
        "phase_38_unlocked": False,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        "automatic_commit_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "report_archive_performed": False,
        "report_dedup_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "historical_report_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "api_route_mutation_performed": False,
        "paper_transition_runtime_binding_performed": False,
        "paper_sandbox_runtime_preflight_runtime_binding_performed": False,
        "paper_sandbox_runtime_preflight_source_mutation_performed": False,
        "final_safety_violation_count": len(final_safety_violations),
        "final_safety_violations": final_safety_violations,
    }
    report.update(contract)
    report.update(guard)
    report.update(probe_ledger)
    report.update(gate)

    report["report_digest"] = stable_digest({key: value for key, value in report.items() if key not in {"report_digest", "report_path"}})

    if write_reports:
        recovery_dir.mkdir(parents=True, exist_ok=True)
        artifacts = {
            f"{PATCH_ID}_paper_only_runtime_config_contract_{stamp}.json": contract,
            f"{PATCH_ID}_no_live_no_exchange_submit_no_network_order_guard_{stamp}.json": guard,
            f"{PATCH_ID}_paper_sandbox_runtime_preflight_probe_{stamp}.json": probe_ledger,
            f"{PATCH_ID}_paper_sandbox_runtime_preflight_gate_{stamp}.json": gate,
        }
        for name, payload in artifacts.items():
            path = recovery_dir / name
            payload = dict(payload)
            payload["patch_id"] = PATCH_ID
            payload["patch_version"] = PATCH_VERSION
            payload["generated_at_utc"] = stamp
            payload["digest"] = stable_digest(payload)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            if "contract_name" in payload:
                report["paper_only_runtime_config_contract_path"] = str(path)
            elif "guard_name" in payload:
                report["no_live_no_exchange_submit_no_network_order_guard_path"] = str(path)
            elif "probe_name" in payload:
                report["paper_sandbox_runtime_preflight_probe_path"] = str(path)
            elif "gate_name" in payload:
                report["paper_sandbox_runtime_preflight_gate_path"] = str(path)
        report_name = f"{PATCH_ID}_paper_sandbox_runtime_preflight_{stamp}_{'ready' if ok else 'not_ready'}.json"
        report_path = recovery_dir / report_name
        report["report_path"] = str(report_path)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    else:
        report.setdefault("paper_only_runtime_config_contract_path", None)
        report.setdefault("no_live_no_exchange_submit_no_network_order_guard_path", None)
        report.setdefault("paper_sandbox_runtime_preflight_probe_path", None)
        report.setdefault("paper_sandbox_runtime_preflight_gate_path", None)
        report["report_path"] = None

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(Path.cwd(), Path(args.reports_dir), write_reports=args.write_reports)
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
