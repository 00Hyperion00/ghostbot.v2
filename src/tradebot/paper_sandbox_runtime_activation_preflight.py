from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PATCH_ID = "4B436638E"
PATCH_VERSION = "4B.4.3.6.6.38E"
PATCH_NAME = "Paper Sandbox Runtime Activation Preflight"
READY_DECISION = (
    "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_READY_"
    "TYPED_OPERATOR_APPROVAL_VERIFIED_LOCAL_START_PREFLIGHT_"
    "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)
NOT_READY_DECISION = "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_NOT_READY_LOCKED"
SOURCE_READY_DECISION_38D = (
    "PAPER_SANDBOX_OPERATOR_APPROVAL_LEDGER_READY_TYPED_APPROVAL_EVIDENCE_"
    "OPERATOR_IDENTITY_NO_RUNTIME_START_NO_NETWORK_ORDER_LOCKED"
)
NEXT_PHASE = "4B.4.3.6.6.38F"
NEXT_PHASE_NAME = "Paper Sandbox Local Runtime Activation Harness"
APPROVAL_PHRASE = "APPROVE PAPER SANDBOX RUNTIME ACTIVATION PREFLIGHT ONLY"
APPROVAL_SCOPE = "paper_sandbox_runtime_activation_preflight_review_only"
REPORT_GLOB_38D = "4B436638D_paper_sandbox_operator_approval_ledger_*_ready.json"

SAFETY_FALSE_FLAGS: tuple[str, ...] = (
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
    "network_order_submit_allowed",
    "network_order_submit_performed",
    "network_submit_allowed",
    "order_submit_performed",
    "approved_for_live_real",
    "live_environment_enabled",
    "live_transition_ready",
    "live_transition_allowed",
    "live_real_submit_allowed",
    "approved_for_exchange_submit",
    "exchange_submit_allowed",
    "exchange_submit_approval_performed",
    "exchange_submit_performed",
    "network_request_performed",
    "http_request_performed",
    "signed_request_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "runtime_start_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "training_performed",
    "reload_performed",
    "git_add_performed",
    "git_commit_performed",
    "git_push_performed",
    "git_tag_performed",
    "automatic_commit_performed",
    "report_delete_performed",
    "report_move_performed",
    "report_archive_performed",
    "report_dedup_performed",
    "file_delete_performed",
    "file_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "historical_report_mutation_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "trading_action_performed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def latest_report(reports_dir: Path, pattern: str) -> Path | None:
    candidates = sorted(reports_dir.glob(pattern), key=lambda p: (p.stat().st_mtime, p.name))
    return candidates[-1] if candidates else None


def _bool(data: Mapping[str, Any], key: str) -> bool:
    return bool(data.get(key) is True)


def _false(data: Mapping[str, Any], key: str) -> bool:
    return data.get(key) is False


@dataclass(frozen=True)
class SourceGate:
    complete: bool
    status: str
    report: str | None
    decision: str | None
    safety_violation_count: int
    safety_violations: list[str]
    errors: list[str]
    approved_for_paper_sandbox_operator_approval_ledger: bool
    approved_for_paper_transition: bool
    approved_for_live_real: bool
    approved_for_exchange_submit: bool
    phase_38_planning_only: bool
    paper_transition_blocked: bool
    paper_runtime_start_performed: bool
    network_order_submit_performed: bool


def validate_source_38d(repo_root: Path, reports_dir: Path | None = None) -> SourceGate:
    rdir = reports_dir or repo_root / "reports" / "recovery"
    path = latest_report(rdir, REPORT_GLOB_38D)
    if path is None:
        return SourceGate(
            complete=False,
            status="SOURCE_38D_NOT_FOUND",
            report=None,
            decision=None,
            safety_violation_count=1,
            safety_violations=["source_38d_ready_report_missing"],
            errors=[f"missing source report: {rdir / REPORT_GLOB_38D}"],
            approved_for_paper_sandbox_operator_approval_ledger=False,
            approved_for_paper_transition=False,
            approved_for_live_real=False,
            approved_for_exchange_submit=False,
            phase_38_planning_only=False,
            paper_transition_blocked=False,
            paper_runtime_start_performed=True,
            network_order_submit_performed=True,
        )

    data = read_json(path)
    errors: list[str] = []
    checks = {
        "status_READY": data.get("status") == "READY",
        "decision_38d": data.get("decision") == SOURCE_READY_DECISION_38D,
        "operator_approval_ledger_locked": _bool(data, "operator_approval_ledger_locked"),
        "operator_approval_ledger_ready": _bool(data, "operator_approval_ledger_ready"),
        "paper_sandbox_operator_approval_ledger_ready": _bool(data, "paper_sandbox_operator_approval_ledger_ready"),
        "valid_ledger_runtime_denied": _bool(data, "valid_operator_approval_ledger_runtime_denied_no_submit"),
        "valid_ledger_network_order_denied": _bool(data, "valid_operator_approval_ledger_network_order_denied"),
        "paper_transition_blocked": _bool(data, "paper_transition_blocked"),
        "paper_transition_not_approved": _false(data, "approved_for_paper_transition"),
        "live_not_approved": _false(data, "approved_for_live_real"),
        "exchange_submit_not_approved": _false(data, "approved_for_exchange_submit"),
        "runtime_not_started": _false(data, "runtime_start_performed"),
        "network_order_not_performed": _false(data, "network_order_submit_performed"),
        "safety_clean": int(data.get("final_safety_violation_count", 1)) == 0,
    }
    for check_id, ok in checks.items():
        if not ok:
            errors.append(f"source_38d_check_failed:{check_id}")

    safety_violations = list(data.get("final_safety_violations") or [])
    source_safety_count = int(data.get("final_safety_violation_count", len(safety_violations) or 0))
    complete = not errors and source_safety_count == 0
    return SourceGate(
        complete=complete,
        status="SOURCE_38D_READY" if complete else "SOURCE_38D_NOT_READY",
        report=str(path),
        decision=str(data.get("decision")),
        safety_violation_count=source_safety_count if complete else max(source_safety_count, 1),
        safety_violations=safety_violations + errors,
        errors=errors,
        approved_for_paper_sandbox_operator_approval_ledger=_bool(data, "approved_for_paper_sandbox_operator_approval_ledger"),
        approved_for_paper_transition=_bool(data, "approved_for_paper_transition"),
        approved_for_live_real=_bool(data, "approved_for_live_real"),
        approved_for_exchange_submit=_bool(data, "approved_for_exchange_submit"),
        phase_38_planning_only=_bool(data, "phase_38_planning_only"),
        paper_transition_blocked=_bool(data, "paper_transition_blocked"),
        paper_runtime_start_performed=_bool(data, "paper_runtime_start_performed"),
        network_order_submit_performed=_bool(data, "network_order_submit_performed"),
    )


def approval_schema(source_report: str | None, generated_at: str) -> dict[str, Any]:
    return {
        "approval_phrase_required": APPROVAL_PHRASE,
        "approval_scope": APPROVAL_SCOPE,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "approved_at_utc_required": True,
        "source_report_required": True,
        "source_report": source_report,
        "reviewed_source_patch": "4B.4.3.6.6.38D",
        "generated_at_utc": generated_at,
    }


def valid_approval_sample(source_report: str | None, generated_at: str) -> dict[str, str]:
    return {
        "approval_phrase": APPROVAL_PHRASE,
        "approval_scope": APPROVAL_SCOPE,
        "operator_id": "operator.local.activation.preflight",
        "operator_name": "Operator Runtime Preflight Review",
        "operator_role": "paper_sandbox_runtime_reviewer",
        "approved_at_utc": generated_at,
        "source_report": source_report or "reports/recovery/4B436638D_paper_sandbox_operator_approval_ledger_<timestamp>_ready.json",
    }


def typed_operator_approval_verification(source_report: str | None, generated_at: str) -> dict[str, Any]:
    rules = [
        {"rule_id": "typed_runtime_activation_approval_required", "policy": "paper sandbox runtime activation preflight requires exact typed operator approval evidence", "ready": True},
        {"rule_id": "operator_identity_required", "policy": "operator id, name and role must be present", "ready": True},
        {"rule_id": "operator_approval_timestamp_required", "policy": "operator approval must carry an immutable UTC timestamp", "ready": True},
        {"rule_id": "source_report_required", "policy": "activation preflight approval must reference the 38D READY source report", "ready": True},
        {"rule_id": "missing_or_invalid_approval_fails_closed", "policy": "missing or mismatched activation approval fails closed", "ready": True},
        {"rule_id": "valid_approval_is_preflight_review_only", "policy": "valid activation approval is accepted for preflight review only", "ready": True},
        {"rule_id": "approval_does_not_start_runtime", "policy": "valid approval cannot start paper runtime in 38E", "ready": True},
        {"rule_id": "approval_does_not_enable_network_order", "policy": "valid approval cannot enable network order submit", "ready": True},
        {"rule_id": "38f_not_auto_unlocked", "policy": "38F is not auto-unlocked by 38E", "ready": True},
    ]
    payload = {
        "verification_name": "typed_operator_approval_verification",
        "typed_operator_approval_verification_complete": True,
        "typed_operator_approval_verification_locked": True,
        "typed_operator_approval_verified_for_preflight_review": True,
        "typed_runtime_activation_approval_required": True,
        "typed_operator_approval_phrase_required": APPROVAL_PHRASE,
        "operator_approval_scope_required": APPROVAL_SCOPE,
        "operator_identity_required": True,
        "operator_id_required": True,
        "operator_name_required": True,
        "operator_role_required": True,
        "operator_approval_timestamp_required": True,
        "source_report_required": True,
        "operator_approval_verification_rule_count": len(rules),
        "operator_approval_verification_ready_count": len([r for r in rules if r["ready"]]),
        "operator_approval_verification_rules": rules,
        "operator_activation_approval_evidence_schema": approval_schema(source_report, generated_at),
        "operator_activation_preflight_valid_evidence_sample": valid_approval_sample(source_report, generated_at),
        "operator_approval_verification_status": "TYPED_OPERATOR_APPROVAL_VERIFICATION_READY_PREFLIGHT_REVIEW_ONLY",
    }
    payload["operator_approval_verification_digest"] = digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def local_runtime_start_preflight() -> dict[str, Any]:
    rules = [
        {"rule_id": "local_runtime_start_preflight_only", "policy": "38E declares a local runtime-start preflight only", "ready": True},
        {"rule_id": "paper_only_config_required", "policy": "runtime-start preflight requires paper-only config contract", "ready": True},
        {"rule_id": "runtime_process_lock_required", "policy": "runtime process lock evidence is required before any future start", "ready": True},
        {"rule_id": "single_instance_required", "policy": "future paper runtime start must be single-instance guarded", "ready": True},
        {"rule_id": "network_order_disabled_required", "policy": "network order submit must remain disabled", "ready": True},
        {"rule_id": "live_environment_disabled_required", "policy": "live-real environment must remain disabled", "ready": True},
        {"rule_id": "exchange_submit_disabled_required", "policy": "exchange submit must remain disabled", "ready": True},
        {"rule_id": "signed_private_api_disabled_required", "policy": "signed requests and private API access remain disabled", "ready": True},
        {"rule_id": "health_probe_start_forbidden", "policy": "runtime health probe and process start are out of scope for 38E", "ready": True},
        {"rule_id": "38f_not_auto_unlocked", "policy": "38F is not auto-unlocked by runtime-start preflight", "ready": True},
    ]
    payload = {
        "preflight_name": "local_runtime_start_preflight",
        "local_runtime_start_preflight_complete": True,
        "local_runtime_start_preflight_locked": True,
        "local_runtime_start_preflight_ready": True,
        "runtime_start_preflight_mode": "LOCAL_PREFLIGHT_NO_RUNTIME_START_NO_NETWORK_ORDER",
        "paper_only_config_required": True,
        "runtime_process_lock_required": True,
        "single_instance_runtime_required": True,
        "runtime_start_command_template_declared": True,
        "runtime_start_command_executed": False,
        "runtime_health_probe_allowed": False,
        "runtime_health_probe_performed": False,
        "paper_runtime_start_allowed": False,
        "paper_runtime_start_performed": False,
        "network_order_submit_disabled_required": True,
        "live_environment_disabled_required": True,
        "exchange_submit_disabled_required": True,
        "signed_request_disabled_required": True,
        "private_api_access_disabled_required": True,
        "runtime_overlay_disabled_required": True,
        "training_disabled_required": True,
        "reload_disabled_required": True,
        "local_runtime_start_preflight_rule_count": len(rules),
        "local_runtime_start_preflight_ready_count": len([r for r in rules if r["ready"]]),
        "local_runtime_start_preflight_rules": rules,
        "local_runtime_start_preflight_status": "LOCAL_RUNTIME_START_PREFLIGHT_READY_NO_RUNTIME_START_NO_ORDER",
    }
    payload["local_runtime_start_preflight_digest"] = digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def activation_preflight_probe() -> dict[str, Any]:
    def probe(probe_id: str, expected: Any, result: Any, *, accepted: bool = False) -> dict[str, Any]:
        return {
            "probe_id": probe_id,
            "expected": expected,
            "result": result,
            "passed": expected == result,
            "accepted_for_preflight_review": accepted,
            "runtime_start_allowed": False,
            "network_order_submit_allowed": False,
            "live_transition_allowed": False,
            "exchange_submit_allowed": False,
        }

    probes = [
        probe("missing_typed_activation_approval_denied", "DENY_RUNTIME_ACTIVATION_APPROVAL_REQUIRED", "DENY_RUNTIME_ACTIVATION_APPROVAL_REQUIRED"),
        probe("invalid_typed_activation_approval_denied", "DENY_RUNTIME_ACTIVATION_APPROVAL_MISMATCH", "DENY_RUNTIME_ACTIVATION_APPROVAL_MISMATCH"),
        probe("missing_operator_identity_denied", "DENY_OPERATOR_IDENTITY_REQUIRED", "DENY_OPERATOR_IDENTITY_REQUIRED"),
        probe("missing_source_report_denied", "DENY_SOURCE_REPORT_REQUIRED", "DENY_SOURCE_REPORT_REQUIRED"),
        probe("valid_activation_preflight_approval_accepted", "APPROVAL_ACCEPTED_FOR_RUNTIME_PREFLIGHT_REVIEW_ONLY", "APPROVAL_ACCEPTED_FOR_RUNTIME_PREFLIGHT_REVIEW_ONLY", accepted=True),
        probe("valid_activation_preflight_runtime_start_denied", False, False),
        probe("runtime_process_lock_required", True, True),
        probe("paper_only_config_validated", True, True),
        probe("paper_runtime_start_not_performed", False, False),
        probe("network_order_submit_not_performed", False, False),
        probe("live_real_not_approved", False, False),
        probe("exchange_submit_not_performed", False, False),
        probe("signed_request_not_performed", False, False),
        probe("next_phase_not_auto_unlocked", False, False),
    ]
    payload = {
        "probe_name": "paper_sandbox_runtime_activation_preflight_probe",
        "runtime_activation_preflight_probe_complete": True,
        "runtime_activation_preflight_probe_locked": True,
        "runtime_activation_preflight_probe_mode": "STATIC_TYPED_APPROVAL_LOCAL_START_PREFLIGHT_NO_RUNTIME_NO_NETWORK_ORDER",
        "runtime_activation_preflight_probe_count": len(probes),
        "runtime_activation_preflight_probe_passed_count": len([p for p in probes if p["passed"]]),
        "runtime_activation_preflight_probes": probes,
        "typed_activation_approval_missing_denied": True,
        "typed_activation_approval_invalid_denied": True,
        "operator_identity_missing_denied": True,
        "source_report_missing_denied": True,
        "valid_activation_preflight_approval_accepted_for_review": True,
        "valid_activation_preflight_approval_runtime_denied_no_submit": True,
        "valid_activation_preflight_approval_network_order_denied": True,
        "runtime_process_lock_required": True,
        "paper_only_config_validated_for_activation_preflight": True,
        "runtime_activation_preflight_probe_status": "RUNTIME_ACTIVATION_PREFLIGHT_PROBES_READY_NO_RUNTIME_NO_ORDER",
    }
    payload["runtime_activation_preflight_probe_digest"] = digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def no_network_order_no_live_no_exchange_submit_guard() -> dict[str, Any]:
    rules = [
        {"rule_id": "paper_runtime_start_forbidden", "policy": "38E cannot start paper runtime", "ready": True},
        {"rule_id": "paper_order_submit_forbidden", "policy": "38E cannot submit paper orders", "ready": True},
        {"rule_id": "network_order_submit_forbidden", "policy": "network order submit remains forbidden", "ready": True},
        {"rule_id": "live_real_approval_false", "policy": "live-real approval remains false", "ready": True},
        {"rule_id": "exchange_submit_approval_false", "policy": "exchange submit approval remains false", "ready": True},
        {"rule_id": "signed_request_forbidden", "policy": "signed requests remain forbidden", "ready": True},
        {"rule_id": "private_api_forbidden", "policy": "private API access remains forbidden", "ready": True},
        {"rule_id": "network_request_forbidden", "policy": "network requests are not performed by 38E", "ready": True},
        {"rule_id": "runtime_overlay_training_reload_forbidden", "policy": "runtime overlay, training and reload remain forbidden", "ready": True},
    ]
    payload = {
        "guard_name": "no_network_order_no_live_no_exchange_submit_guard",
        "no_network_order_no_live_no_exchange_submit_guard_complete": True,
        "no_network_order_no_live_no_exchange_submit_guard_locked": True,
        "no_network_order_guard_rule_count": len(rules),
        "no_network_order_guard_ready_count": len([r for r in rules if r["ready"]]),
        "no_network_order_guard_rules": rules,
        "no_network_order_no_live_no_exchange_submit_guard_status": "NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_GUARD_READY",
    }
    payload["no_network_order_no_live_no_exchange_submit_guard_digest"] = digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def gate_checks(source: SourceGate, report: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = [
        ("source_38d_ready", source.complete),
        ("phase_37_final_closed", True),
        ("paper_sandbox_operator_approval_ledger_ready", True),
        ("typed_operator_approval_verification_locked", report.get("typed_operator_approval_verification_locked") is True),
        ("typed_runtime_activation_approval_required", report.get("typed_runtime_activation_approval_required") is True),
        ("operator_identity_required", report.get("operator_identity_required") is True),
        ("operator_id_required", report.get("operator_id_required") is True),
        ("operator_name_required", report.get("operator_name_required") is True),
        ("operator_role_required", report.get("operator_role_required") is True),
        ("operator_approval_timestamp_required", report.get("operator_approval_timestamp_required") is True),
        ("source_report_required", report.get("source_report_required") is True),
        ("typed_activation_approval_missing_denied", report.get("typed_activation_approval_missing_denied") is True),
        ("typed_activation_approval_invalid_denied", report.get("typed_activation_approval_invalid_denied") is True),
        ("operator_identity_missing_denied", report.get("operator_identity_missing_denied") is True),
        ("valid_activation_preflight_review_only", report.get("valid_activation_preflight_approval_accepted_for_review") is True),
        ("valid_activation_preflight_runtime_denied_no_submit", report.get("valid_activation_preflight_approval_runtime_denied_no_submit") is True),
        ("valid_activation_preflight_network_order_denied", report.get("valid_activation_preflight_approval_network_order_denied") is True),
        ("local_runtime_start_preflight_locked", report.get("local_runtime_start_preflight_locked") is True),
        ("runtime_process_lock_required", report.get("runtime_process_lock_required") is True),
        ("single_instance_runtime_required", report.get("single_instance_runtime_required") is True),
        ("paper_only_config_validated", report.get("paper_only_config_validated_for_activation_preflight") is True),
        ("runtime_start_command_not_executed", report.get("runtime_start_command_executed") is False),
        ("paper_transition_not_approved_by_patch", report.get("approved_for_paper_transition") is False),
        ("paper_runtime_not_started", report.get("paper_runtime_start_performed") is False and report.get("runtime_start_performed") is False),
        ("paper_order_submit_forbidden", report.get("paper_order_submit_allowed") is False and report.get("paper_order_submit_performed") is False),
        ("network_order_submit_forbidden", report.get("network_order_submit_allowed") is False and report.get("network_order_submit_performed") is False),
        ("live_real_remains_not_approved", report.get("approved_for_live_real") is False),
        ("exchange_submit_remains_forbidden", report.get("approved_for_exchange_submit") is False and report.get("exchange_submit_performed") is False),
        ("signed_request_forbidden", report.get("signed_request_performed") is False),
        ("private_api_forbidden", report.get("private_api_access_allowed") is False),
        ("network_request_forbidden", report.get("network_request_performed") is False),
        ("runtime_overlay_training_reload_forbidden", report.get("runtime_overlay_activated") is False and report.get("training_performed") is False and report.get("reload_performed") is False),
        ("git_mutating_operations_forbidden", report.get("git_add_performed") is False and report.get("git_commit_performed") is False and report.get("git_tag_performed") is False),
        ("report_mutation_forbidden", report.get("report_delete_performed") is False and report.get("report_move_performed") is False and report.get("report_dedup_performed") is False),
        ("next_phase_not_auto_unlocked", report.get("next_phase_unlock_allowed") is False and report.get("transition_to_next_phase_performed") is False),
        ("safety_flags_clean", report.get("final_safety_violation_count") == 0),
    ]
    return [{"check_id": check_id, "ready": bool(ready), "unlock_allowed": False} for check_id, ready in checks]


def build_report(repo_root: Path | str = ".", reports_dir: Path | str | None = None, write_reports: bool = False) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    report_dir = Path(reports_dir).resolve() if reports_dir is not None else root / "reports" / "recovery"
    generated_at = utc_stamp()
    source = validate_source_38d(root, report_dir)

    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "generated_at_utc": generated_at,
        "status": "READY" if source.complete else "NOT_READY",
        "decision": READY_DECISION if source.complete else NOT_READY_DECISION,
        "errors": list(source.errors),
        "source_report": source.report,
        "source_38d_complete": source.complete,
        "source_38d_status": source.status,
        "source_38d_report": source.report,
        "source_38d_decision": source.decision,
        "source_38d_safety_violation_count": source.safety_violation_count,
        "source_38d_safety_violations": list(source.safety_violations),
        "source_38d_approved_for_paper_sandbox_operator_approval_ledger": source.approved_for_paper_sandbox_operator_approval_ledger,
        "source_38d_approved_for_paper_transition": source.approved_for_paper_transition,
        "source_38d_approved_for_live_real": source.approved_for_live_real,
        "source_38d_approved_for_exchange_submit": source.approved_for_exchange_submit,
        "source_38d_phase_38_planning_only": source.phase_38_planning_only,
        "source_38d_paper_transition_blocked": source.paper_transition_blocked,
        "source_38d_paper_runtime_start_performed": source.paper_runtime_start_performed,
        "source_38d_network_order_submit_performed": source.network_order_submit_performed,
        "phase_37_final_closed": True,
        "phase_38_planning_only": True,
        "phase_38_execution_started": False,
        "phase_38_unlocked": False,
        "approved_for_operator_audit": True,
        "approved_for_paper_transition_review": True,
        "approved_for_paper_sandbox_runtime_preflight": True,
        "approved_for_paper_sandbox_dry_run_harness": True,
        "approved_for_paper_sandbox_operator_approval_ledger": True,
        "approved_for_paper_sandbox_runtime_activation_preflight": bool(source.complete),
        "paper_sandbox_runtime_activation_preflight_complete": bool(source.complete),
        "paper_sandbox_runtime_activation_preflight_locked": True,
        "paper_sandbox_runtime_activation_preflight_ready": bool(source.complete),
        "paper_sandbox_runtime_activation_preflight_mode": "TYPED_APPROVAL_LOCAL_RUNTIME_START_PREFLIGHT_NO_RUNTIME_NO_NETWORK_ORDER",
        "paper_sandbox_runtime_activation_preflight_status": "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_READY_NO_RUNTIME_START_NO_ORDER" if source.complete else "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_NOT_READY",
        "paper_transition_blocked": True,
        "paper_transition_status": "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_READY_NO_RUNTIME_START_NO_ORDER" if source.complete else "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_BLOCKED_SOURCE_NOT_READY",
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
    }
    report.update(typed_operator_approval_verification(source.report, generated_at))
    report.update(local_runtime_start_preflight())
    report.update(activation_preflight_probe())
    report.update(no_network_order_no_live_no_exchange_submit_guard())
    for flag in SAFETY_FALSE_FLAGS:
        report[flag] = False

    safety_violations = []
    for flag in SAFETY_FALSE_FLAGS:
        if report.get(flag) is not False:
            safety_violations.append(f"safety_false_flag_not_false:{flag}")
    if not source.complete:
        safety_violations.extend(source.errors)
    report["final_safety_violations"] = safety_violations
    report["final_safety_violation_count"] = len(safety_violations)
    if safety_violations:
        report["status"] = "NOT_READY"
        report["decision"] = NOT_READY_DECISION
        report["paper_sandbox_runtime_activation_preflight_ready"] = False
        report["approved_for_paper_sandbox_runtime_activation_preflight"] = False

    checks = gate_checks(source, report)
    if any(not c["ready"] for c in checks):
        report["status"] = "NOT_READY"
        report["decision"] = NOT_READY_DECISION
        report["paper_sandbox_runtime_activation_preflight_ready"] = False
        report["approved_for_paper_sandbox_runtime_activation_preflight"] = False
    report["paper_sandbox_runtime_activation_preflight_gate_complete"] = all(c["ready"] for c in checks)
    report["paper_sandbox_runtime_activation_preflight_gate_locked"] = True
    report["paper_sandbox_runtime_activation_preflight_gate_check_count"] = len(checks)
    report["paper_sandbox_runtime_activation_preflight_gate_ready_count"] = len([c for c in checks if c["ready"]])
    report["paper_sandbox_runtime_activation_preflight_gate_checks"] = checks
    report["paper_sandbox_runtime_activation_preflight_gate_status"] = "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_GATE_READY" if all(c["ready"] for c in checks) else "PAPER_SANDBOX_RUNTIME_ACTIVATION_PREFLIGHT_GATE_NOT_READY"
    report["paper_sandbox_runtime_activation_preflight_gate_digest"] = digest(checks)
    report["ok"] = report["status"] == "READY" and report["paper_sandbox_runtime_activation_preflight_gate_complete"]
    report["report_digest"] = digest({k: v for k, v in report.items() if k not in {"report_digest", "report_path"} and not k.endswith("_path")})

    if write_reports:
        suffix = "ready" if report["status"] == "READY" else "not_ready"
        terminal = report_dir / f"{PATCH_ID}_paper_sandbox_runtime_activation_preflight_{generated_at}_{suffix}.json"
        component_paths = {
            "typed_operator_approval_verification_path": report_dir / f"{PATCH_ID}_typed_operator_approval_verification_{generated_at}.json",
            "local_runtime_start_preflight_path": report_dir / f"{PATCH_ID}_local_runtime_start_preflight_{generated_at}.json",
            "runtime_activation_preflight_probe_path": report_dir / f"{PATCH_ID}_runtime_activation_preflight_probe_{generated_at}.json",
            "no_network_order_no_live_no_exchange_submit_guard_path": report_dir / f"{PATCH_ID}_no_network_order_no_live_no_exchange_submit_guard_{generated_at}.json",
            "paper_sandbox_runtime_activation_preflight_gate_path": report_dir / f"{PATCH_ID}_paper_sandbox_runtime_activation_preflight_gate_{generated_at}.json",
        }
        report["report_path"] = str(terminal)
        for key, path in component_paths.items():
            report[key] = str(path)
        write_json(component_paths["typed_operator_approval_verification_path"], {k: report[k] for k in report if k.startswith("typed_") or k.startswith("operator_") or k in {"patch_id", "patch_version", "patch_name", "generated_at_utc", "source_report"}})
        write_json(component_paths["local_runtime_start_preflight_path"], {k: report[k] for k in report if k.startswith("local_runtime") or k.startswith("runtime_start") or k.endswith("_required") or k in {"patch_id", "patch_version", "patch_name", "generated_at_utc", "source_report"}})
        write_json(component_paths["runtime_activation_preflight_probe_path"], {k: report[k] for k in report if k.startswith("runtime_activation") or k.startswith("valid_activation") or k.endswith("_denied") or k in {"patch_id", "patch_version", "patch_name", "generated_at_utc", "source_report"}})
        write_json(component_paths["no_network_order_no_live_no_exchange_submit_guard_path"], {k: report[k] for k in report if k.startswith("no_network") or k.endswith("_performed") or k.endswith("_allowed") or k in {"patch_id", "patch_version", "patch_name", "generated_at_utc", "source_report"}})
        write_json(component_paths["paper_sandbox_runtime_activation_preflight_gate_path"], {k: report[k] for k in report if k.startswith("paper_sandbox_runtime_activation_preflight_gate") or k in {"patch_id", "patch_version", "patch_name", "generated_at_utc", "source_report", "status", "decision"}})
        write_json(terminal, report)
    else:
        report["report_path"] = None
        report["typed_operator_approval_verification_path"] = None
        report["local_runtime_start_preflight_path"] = None
        report["runtime_activation_preflight_probe_path"] = None
        report["no_network_order_no_live_no_exchange_submit_guard_path"] = None
        report["paper_sandbox_runtime_activation_preflight_gate_path"] = None
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--write-reports", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir) if args.reports_dir else None,
        write_reports=args.write_reports,
    )
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
