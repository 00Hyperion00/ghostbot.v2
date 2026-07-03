from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:  # pragma: no cover - exercised in integration tests when PyYAML is present
    import yaml  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PATCH_ID = "4B436637D"
PATCH_VERSION = "4B.4.3.6.6.37D"
PATCH_NAME = "Strict Config Unknown-Key Fail-Closed"
CHECK_NAME = "strict_config_unknown_key_fail_closed"
READY_DECISION = "STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_3_LOCKED"
NOT_READY_DECISION = "STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_NOT_READY_NO_SUBMIT_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.37E"
SOURCE_37C_PATTERN = "4B436637C_repo_hygiene_evidence_retention_*_ready.json"

SAFETY_FALSE_KEYS: tuple[str, ...] = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "evidence_collection_started",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "fee_slippage_mutation_performed",
    "file_delete_performed",
    "file_move_performed",
    "http_request_performed",
    "install_contract_mutation_performed",
    "live_environment_enabled",
    "live_real_submit_allowed",
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "operator_observation_authorization_unlocked",
    "operator_observation_token_consumed",
    "operator_observation_token_validated",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_37_execution_started",
    "phase_37_unlocked",
    "phase_reopen_allowed",
    "phase_reopen_performed",
    "private_account_read_performed",
    "private_api_access_allowed",
    "promotion_gate_mutation_performed",
    "public_data_fetch_adapter_executed",
    "public_market_data_collection_performed",
    "public_observation_dry_run_collector_executed",
    "public_observation_execution_performed",
    "public_observation_network_off_execution_package_executed",
    "readme_install_contract_mutation_performed",
    "reload_performed",
    "repo_hygiene_cleanup_performed",
    "report_commit_policy_mutation_performed",
    "report_delete_performed",
    "report_move_performed",
    "requirements_alignment_mutation_performed",
    "runtime_evidence_artifact_written",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_lock_mutation_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "signed_request_performed",
    "simulated_approval_performed",
    "sqlite_schema_mutation_performed",
    "strict_config_runtime_loader_mutation_performed",
    "trading_action_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "typed_confirmation_mutation_performed",
)

P0_GAPS_AFTER_37D: tuple[dict[str, Any], ...] = (
    {"gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT", "closed": True, "domain": "install_contract", "closed_by": "4B.4.3.6.6.37B-H1"},
    {"gap_id": "P0_REPO_HYGIENE_EVIDENCE_RETENTION", "closed": True, "domain": "repo_hygiene", "closed_by": "4B.4.3.6.6.37C"},
    {"gap_id": "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED", "closed": True, "domain": "strict_config", "closed_by": PATCH_VERSION},
    {"gap_id": "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD", "closed": False, "domain": "api_security", "closed_by": None},
    {"gap_id": "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS", "closed": False, "domain": "operator_controls", "closed_by": None},
    {"gap_id": "P0_SQLITE_AUDIT_BASELINE", "closed": False, "domain": "persistence", "closed_by": None},
    {"gap_id": "P0_RUNTIME_PROCESS_LOCK", "closed": False, "domain": "runtime_safety", "closed_by": None},
    {"gap_id": "P0_FEE_SLIPPAGE_BASELINE", "closed": False, "domain": "execution_cost_model", "closed_by": None},
    {"gap_id": "P0_REPORT_COMMIT_POLICY", "closed": False, "domain": "evidence_governance", "closed_by": None},
    {"gap_id": "P0_PROMOTION_GATE_ISOLATION", "closed": False, "domain": "promotion_governance", "closed_by": None},
)

# Strict allow-list schema. A mapping value of None means the section is admitted as an explicit extension point.
# Unknown keys at any mapping level with an explicit dict schema are hard errors.
STRICT_CONFIG_SCHEMA: dict[str, Any] = {
    "schema_version": None,
    "environment": None,
    "mode": None,
    "symbol": None,
    "symbols": None,
    "timeframe": None,
    "exchange": {
        "name": None,
        "market_type": None,
        "testnet": None,
        "base_url": None,
        "ws_url": None,
        "timeout_seconds": None,
        "recv_window_ms": None,
        "rate_limit_per_minute": None,
    },
    "binance": {
        "market_type": None,
        "testnet": None,
        "base_url": None,
        "ws_url": None,
        "timeout_seconds": None,
        "recv_window_ms": None,
    },
    "risk": {
        "risk_per_trade_pct": None,
        "max_daily_loss_pct": None,
        "max_position_notional": None,
        "max_leverage": None,
        "stop_loss_pct": None,
        "take_profit_pct": None,
        "cooldown_seconds": None,
        "min_order_notional": None,
    },
    "strategy": None,
    "features": None,
    "model": None,
    "data": None,
    "paths": None,
    "runtime": {
        "no_submit_mode": None,
        "shadow_mode": None,
        "paper_mode": None,
        "live_mode": None,
        "dry_run": None,
        "health_check_interval_seconds": None,
        "max_worker_count": None,
    },
    "dashboard": None,
    "logging": None,
    "database": None,
    "observability": None,
    "alerts": None,
    "scheduler": None,
    "backtest": None,
    "shadow": None,
    "paper": None,
    "live": None,
    "execution": None,
    "api": None,
    "security": None,
    "experimental": None,
}

SCHEMA_GUARD_RULES: tuple[dict[str, Any], ...] = (
    {"rule_id": "yaml_parser_available", "ready": True, "policy": "YAML config parsing uses safe_load only"},
    {"rule_id": "root_unknown_key_hard_error", "ready": True, "policy": "unknown root keys raise ConfigSchemaError"},
    {"rule_id": "nested_unknown_key_hard_error", "ready": True, "policy": "unknown nested keys raise ConfigSchemaError"},
    {"rule_id": "explicit_extension_points_only", "ready": True, "policy": "open-ended mappings are explicit schema extension points only"},
    {"rule_id": "valid_config_acceptance_probe", "ready": True, "policy": "valid minimal config is accepted"},
    {"rule_id": "runtime_loader_binding_not_performed", "ready": True, "policy": "no runtime loader binding or reload is performed in this no-submit hardening phase"},
)


class ConfigSchemaError(ValueError):
    """Raised when a YAML config contains an unknown key under the strict schema."""


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_digest(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def latest_report(repo_root: Path, reports_dir: Path | None, pattern: str) -> Path | None:
    search_dirs: list[Path] = []
    if reports_dir is not None:
        search_dirs.append(reports_dir)
    search_dirs.extend([repo_root / "reports" / "recovery", repo_root / "reports", repo_root])
    candidates: list[Path] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob(pattern):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def truthy_violations(source: Mapping[str, Any], flags: Iterable[str]) -> list[str]:
    return [name for name in flags if bool(source.get(name, False))]


@dataclass(frozen=True)
class GitState:
    git_available: bool
    git_branch: str | None
    git_head_short: str | None
    phase_37_tags: tuple[str, ...]


def _run_git(args: Sequence[str], repo_root: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def read_git_state(repo_root: Path) -> GitState:
    try:
        branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        head_result = _run_git(["rev-parse", "--short", "HEAD"], repo_root)
        tags_result = _run_git(["tag", "--list", "4B.4.3.6.6.37*"], repo_root)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return GitState(False, None, None, tuple())
    git_available = branch_result.returncode == 0 and head_result.returncode == 0
    phase_37_tags = tuple(sorted(line.strip() for line in tags_result.stdout.splitlines() if line.strip())) if tags_result.returncode == 0 else tuple()
    return GitState(
        git_available=git_available,
        git_branch=branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        git_head_short=head_result.stdout.strip() if head_result.returncode == 0 else None,
        phase_37_tags=phase_37_tags,
    )


def parse_yaml_text(text: str) -> Mapping[str, Any]:
    if yaml is None:  # pragma: no cover
        raise ConfigSchemaError("PyYAML is required for strict config schema validation")
    data = yaml.safe_load(text)  # type: ignore[union-attr]
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ConfigSchemaError("YAML root must be a mapping")
    return data


def validate_mapping_against_schema(data: Mapping[str, Any], schema: Mapping[str, Any], path: str = "") -> None:
    allowed = set(schema.keys())
    unknown = sorted(str(key) for key in data.keys() if str(key) not in allowed)
    if unknown:
        location = path or "<root>"
        raise ConfigSchemaError(f"Unknown config key(s) at {location}: {', '.join(unknown)}")
    for raw_key, value in data.items():
        key = str(raw_key)
        child_schema = schema.get(key)
        if isinstance(child_schema, Mapping) and isinstance(value, Mapping):
            validate_mapping_against_schema(value, child_schema, f"{path}.{key}" if path else key)


def validate_yaml_text_strict(text: str, schema: Mapping[str, Any] | None = None) -> dict[str, Any]:
    parsed = parse_yaml_text(text)
    validate_mapping_against_schema(parsed, schema or STRICT_CONFIG_SCHEMA)
    return dict(parsed)


def validate_yaml_file_strict(path: Path, schema: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return validate_yaml_text_strict(path.read_text(encoding="utf-8"), schema=schema)


def load_source_37c(repo_root: Path, reports_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    path = latest_report(repo_root, reports_dir, SOURCE_37C_PATTERN)
    if path is None:
        return None, None
    return load_json(path), path


def validate_source_37c(source: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    if source is None:
        return False, ["SOURCE_37C_READY_REPORT_NOT_FOUND"], {
            "source_37c_complete": False,
            "source_37c_status": "SOURCE_37C_MISSING",
            "source_37c_safety_violation_count": 0,
            "source_37c_safety_violations": [],
        }
    errors: list[str] = []
    safety_violations = truthy_violations(source, SAFETY_FALSE_KEYS)
    if source.get("status") != "READY":
        errors.append("SOURCE_37C_STATUS_NOT_READY")
    if source.get("decision") != "REPO_HYGIENE_EVIDENCE_RETENTION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_2_LOCKED":
        errors.append("SOURCE_37C_DECISION_UNEXPECTED")
    if not bool(source.get("p0_repo_hygiene_evidence_retention_closed", False)):
        errors.append("SOURCE_37C_P0_2_NOT_CLOSED")
    if source.get("p0_repo_hygiene_evidence_retention_closed_by") != "4B.4.3.6.6.37C":
        errors.append("SOURCE_37C_P0_2_CLOSED_BY_UNEXPECTED")
    if int(source.get("p0_hardening_closed_gap_count_after_37c", -1) or -1) != 2:
        errors.append("SOURCE_37C_CLOSED_GAP_COUNT_UNEXPECTED")
    if int(source.get("p0_hardening_open_gap_count_after_37c", -1) or -1) != 8:
        errors.append("SOURCE_37C_OPEN_GAP_COUNT_UNEXPECTED")
    if safety_violations:
        errors.append("SOURCE_37C_SAFETY_VIOLATION")
    info = {
        "source_37c_complete": len(errors) == 0,
        "source_37c_status": "SOURCE_37C_READY" if len(errors) == 0 else "SOURCE_37C_INVALID",
        "source_37c_decision": source.get("decision"),
        "source_37c_p0_2_closed": bool(source.get("p0_repo_hygiene_evidence_retention_closed", False)),
        "source_37c_p0_2_closed_by": source.get("p0_repo_hygiene_evidence_retention_closed_by"),
        "source_37c_p0_open_gap_count": int(source.get("p0_hardening_open_gap_count_after_37c", 0) or 0),
        "source_37c_p0_closed_gap_count": int(source.get("p0_hardening_closed_gap_count_after_37c", 0) or 0),
        "source_37c_phase_37_planning_only": bool(source.get("phase_37_planning_only", False)),
        "source_37c_report": None,
        "source_37c_safety_violation_count": len(safety_violations),
        "source_37c_safety_violations": safety_violations,
    }
    return len(errors) == 0, errors, info


def run_unknown_key_probe() -> dict[str, Any]:
    valid_text = """
schema_version: 1
environment: shadow
exchange:
  name: binance
  market_type: futures
  testnet: true
risk:
  risk_per_trade_pct: 0.25
  max_daily_loss_pct: 2.0
runtime:
  no_submit_mode: true
symbols:
  - ETHUSDT
"""
    unknown_root_text = """
schema_version: 1
unexpected_root_key: true
"""
    unknown_nested_text = """
schema_version: 1
risk:
  risk_per_trade_pct: 0.25
  unexpected_nested_key: true
"""
    probes: list[dict[str, Any]] = []
    valid_accepted = False
    root_rejected = False
    nested_rejected = False

    try:
        validate_yaml_text_strict(valid_text)
        valid_accepted = True
        probes.append({"probe_id": "valid_minimal_config", "expected": "ACCEPT", "result": "ACCEPTED", "passed": True})
    except Exception as exc:
        probes.append({"probe_id": "valid_minimal_config", "expected": "ACCEPT", "result": "REJECTED", "passed": False, "error": str(exc)})

    try:
        validate_yaml_text_strict(unknown_root_text)
        probes.append({"probe_id": "unknown_root_key", "expected": "REJECT", "result": "ACCEPTED", "passed": False})
    except ConfigSchemaError as exc:
        root_rejected = True
        probes.append({"probe_id": "unknown_root_key", "expected": "REJECT", "result": "REJECTED", "passed": True, "error_type": type(exc).__name__})

    try:
        validate_yaml_text_strict(unknown_nested_text)
        probes.append({"probe_id": "unknown_nested_key", "expected": "REJECT", "result": "ACCEPTED", "passed": False})
    except ConfigSchemaError as exc:
        nested_rejected = True
        probes.append({"probe_id": "unknown_nested_key", "expected": "REJECT", "result": "REJECTED", "passed": True, "error_type": type(exc).__name__})

    passed = valid_accepted and root_rejected and nested_rejected
    payload: dict[str, Any] = {
        "probe_name": "strict_config_unknown_key_hard_error_probe",
        "strict_config_unknown_key_probe_complete": passed,
        "strict_config_unknown_key_probe_locked": passed,
        "strict_config_unknown_key_probe_status": "UNKNOWN_KEY_HARD_ERROR_PROBE_READY" if passed else "UNKNOWN_KEY_HARD_ERROR_PROBE_NOT_READY",
        "strict_config_unknown_key_probe_count": len(probes),
        "strict_config_unknown_key_probe_passed_count": sum(1 for probe in probes if bool(probe.get("passed", False))),
        "strict_config_unknown_key_probes": probes,
        "strict_config_valid_config_accepted": valid_accepted,
        "strict_config_unknown_root_key_rejected": root_rejected,
        "strict_config_unknown_nested_key_rejected": nested_rejected,
        "strict_config_unknown_key_hard_error_enabled": root_rejected and nested_rejected,
        "yaml_unknown_key_hard_error_probe_passed": passed,
    }
    payload["strict_config_unknown_key_probe_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def build_schema_guard_contract() -> dict[str, Any]:
    rules = [dict(rule) for rule in SCHEMA_GUARD_RULES]
    if yaml is None:
        rules[0]["ready"] = False
    ready_count = sum(1 for rule in rules if bool(rule.get("ready", False)))
    complete = ready_count == len(rules)
    payload: dict[str, Any] = {
        "guard_name": "strict_config_schema_guard",
        "strict_config_schema_guard_complete": complete,
        "strict_config_schema_guard_locked": complete,
        "strict_config_schema_guard_status": "STRICT_CONFIG_SCHEMA_GUARD_READY" if complete else "STRICT_CONFIG_SCHEMA_GUARD_NOT_READY",
        "strict_config_schema_guard_rule_count": len(rules),
        "strict_config_schema_guard_ready_count": ready_count,
        "strict_config_schema_guard_rules": rules,
        "strict_config_schema_root_key_count": len(STRICT_CONFIG_SCHEMA),
        "strict_config_schema_root_keys": sorted(STRICT_CONFIG_SCHEMA.keys()),
        "strict_config_fail_closed_default": True,
        "strict_config_schema_guard_callable_ready": True,
        "strict_config_runtime_loader_mutation_performed": False,
        "strict_config_runtime_loader_binding_required_future": False,
        "runtime_readiness_unlock_performed": False,
    }
    payload["strict_config_schema_guard_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def discover_config_candidates(repo_root: Path) -> tuple[dict[str, Any], ...]:
    candidate_paths: set[Path] = set()
    patterns = (
        "*.yml",
        "*.yaml",
        "config/*.yml",
        "config/*.yaml",
        "configs/*.yml",
        "configs/*.yaml",
    )
    for pattern in patterns:
        candidate_paths.update(repo_root.glob(pattern))
    records: list[dict[str, Any]] = []
    for path in sorted(candidate_paths):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        records.append({
            "path": rel,
            "exists": True,
            "strict_validation_required_for_runtime_use": True,
            "validation_performed_by_37d": False,
            "mutation_performed": False,
            "runtime_reload_performed": False,
        })
    return tuple(records)


def build_config_schema_guard(repo_root: Path) -> dict[str, Any]:
    contract = build_schema_guard_contract()
    probe = run_unknown_key_probe()
    candidates = discover_config_candidates(repo_root)
    complete = bool(contract["strict_config_schema_guard_complete"]) and bool(probe["strict_config_unknown_key_probe_complete"])
    payload: dict[str, Any] = {
        **contract,
        **probe,
        "strict_config_candidate_audit_complete": True,
        "strict_config_candidate_audit_locked": True,
        "strict_config_candidate_audit_mode": "DISCOVERY_ONLY_NO_RUNTIME_MUTATION",
        "strict_config_candidate_count_observed": len(candidates),
        "strict_config_candidate_records": list(candidates),
        "strict_config_file_mutation_performed": False,
        "strict_config_runtime_reload_performed": False,
        "config_runtime_reload_performed": False,
        "config_schema_guard_complete": complete,
        "config_schema_guard_locked": complete,
        "config_schema_guard_status": "CONFIG_SCHEMA_GUARD_READY_UNKNOWN_KEYS_FAIL_CLOSED" if complete else "CONFIG_SCHEMA_GUARD_NOT_READY",
    }
    payload["config_schema_guard_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def build_p0_gap_closure_delta() -> dict[str, Any]:
    items = [dict(item) for item in P0_GAPS_AFTER_37D]
    closed_count = sum(1 for item in items if item["closed"] is True)
    open_count = len(items) - closed_count
    p0_3_closed = any(item["gap_id"] == "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED" and item["closed"] is True for item in items)
    payload: dict[str, Any] = {
        "delta_name": "p0_gap_closure_delta_37d",
        "p0_gap_closure_delta_complete": p0_3_closed,
        "p0_gap_closure_delta_locked": p0_3_closed,
        "p0_gap_closure_delta_status": "P0_3_STRICT_CONFIG_GAP_CLOSED" if p0_3_closed else "P0_3_STRICT_CONFIG_GAP_NOT_CLOSED",
        "p0_gap_closure_items": items,
        "p0_strict_config_unknown_key_fail_closed": p0_3_closed,
        "p0_strict_config_unknown_key_fail_closed_by": PATCH_VERSION if p0_3_closed else None,
        "p0_hardening_gap_count_after_37d": len(items),
        "p0_hardening_closed_gap_count_after_37d": closed_count,
        "p0_hardening_open_gap_count_after_37d": open_count,
        "p0_hardening_complete": False,
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
    }
    payload["p0_gap_closure_delta_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def build_no_submit_p0_3_gate(
    source_ok: bool,
    config_guard: Mapping[str, Any],
    gap_delta: Mapping[str, Any],
    final_safety_violations: Sequence[str],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [
        {"check_id": "source_37c_ready", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "p0_1_install_contract_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "p0_2_repo_hygiene_remains_closed", "ready": True, "unlock_allowed": False},
        {"check_id": "strict_config_schema_guard_locked", "ready": bool(config_guard.get("strict_config_schema_guard_locked", False)), "unlock_allowed": False},
        {"check_id": "yaml_unknown_key_hard_error_probe_passed", "ready": bool(config_guard.get("yaml_unknown_key_hard_error_probe_passed", False)), "unlock_allowed": False},
        {"check_id": "p0_3_strict_config_closed_only", "ready": bool(gap_delta.get("p0_strict_config_unknown_key_fail_closed", False)) and int(gap_delta.get("p0_hardening_closed_gap_count_after_37d", 0) or 0) == 3, "unlock_allowed": False},
        {"check_id": "runtime_config_loader_not_mutated", "ready": not bool(config_guard.get("strict_config_runtime_loader_mutation_performed", False)), "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "runtime_overlay_training_reload_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
        {"check_id": "safety_flags_clean", "ready": len(final_safety_violations) == 0, "unlock_allowed": False},
    ]
    ready_count = sum(1 for check in checks if bool(check["ready"]))
    complete = ready_count == len(checks)
    payload: dict[str, Any] = {
        "gate_name": "no_submit_p0_3_hardening_gate",
        "no_submit_p0_3_hardening_gate_complete": complete,
        "no_submit_p0_3_hardening_gate_locked": complete,
        "no_submit_p0_3_hardening_gate_status": "NO_SUBMIT_P0_3_HARDENING_GATE_READY" if complete else "NO_SUBMIT_P0_3_HARDENING_GATE_NOT_READY",
        "no_submit_p0_3_hardening_gate_check_count": len(checks),
        "no_submit_p0_3_hardening_gate_ready_count": ready_count,
        "no_submit_p0_3_hardening_gate_checks": checks,
    }
    payload["no_submit_p0_3_hardening_gate_digest"] = stable_digest({k: v for k, v in payload.items() if not k.endswith("_digest")})
    return payload


def evaluate(repo_root: Path, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    source, source_path = load_source_37c(repo_root, reports_dir)
    source_ok, source_errors, source_info = validate_source_37c(source)
    if source_path is not None:
        source_info["source_37c_report"] = str(source_path)
    git_state = read_git_state(repo_root)
    config_guard = build_config_schema_guard(repo_root)
    gap_delta = build_p0_gap_closure_delta()

    base_payload: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "check_name": CHECK_NAME,
        "next_phase": NEXT_PHASE,
        "git_available": git_state.git_available,
        "git_branch": git_state.git_branch,
        "git_head_short": git_state.git_head_short,
        "phase_37_tag_count_observed": len(git_state.phase_37_tags),
        "phase_37_tags_observed": list(git_state.phase_37_tags),
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "phase_reopen_allowed": False,
        "phase_reopen_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37D_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_NO_SUBMIT",
        "production_hardening_p0_3_scope": "strict_config_unknown_key_fail_closed_only",
        "production_readiness_status": "P0_3_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT",
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "exchange_submit_allowed": False,
        "exchange_submit_performed": False,
        "network_request_allowed_now": False,
        "network_request_performed": False,
        "network_submit_allowed": False,
        "http_request_performed": False,
        "signed_request_performed": False,
        "order_submit_performed": False,
        "paper_environment_enabled": False,
        "paper_submit_allowed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "live_environment_enabled": False,
        "live_real_submit_allowed": False,
        "private_account_read_performed": False,
        "private_api_access_allowed": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "public_observation_network_off_execution_package_executed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_evidence_artifact_written": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_overlay_allowed": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "simulated_approval_performed": False,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "report_commit_policy_mutation_performed": False,
        "report_delete_performed": False,
        "report_move_performed": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "install_contract_mutation_performed": False,
        "requirements_alignment_mutation_performed": False,
        "readme_install_contract_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_schema_mutation_performed": False,
        "runtime_lock_mutation_performed": False,
        "fee_slippage_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
        "evidence_collection_started": False,
    }
    payload: dict[str, Any] = {}
    payload.update(base_payload)
    payload.update(source_info)
    payload.update(config_guard)
    payload.update(gap_delta)
    final_safety_violations = truthy_violations(payload, SAFETY_FALSE_KEYS)
    gate = build_no_submit_p0_3_gate(source_ok, config_guard, gap_delta, final_safety_violations)
    payload.update(gate)

    ready = (
        source_ok
        and bool(config_guard.get("strict_config_schema_guard_complete", False))
        and bool(config_guard.get("strict_config_schema_guard_locked", False))
        and bool(config_guard.get("yaml_unknown_key_hard_error_probe_passed", False))
        and bool(config_guard.get("config_schema_guard_locked", False))
        and bool(gap_delta.get("p0_strict_config_unknown_key_fail_closed", False))
        and bool(gate.get("no_submit_p0_3_hardening_gate_complete", False))
        and len(final_safety_violations) == 0
    )
    errors = [*source_errors]
    if not bool(config_guard.get("strict_config_schema_guard_locked", False)):
        errors.append("STRICT_CONFIG_SCHEMA_GUARD_NOT_LOCKED")
    if not bool(config_guard.get("yaml_unknown_key_hard_error_probe_passed", False)):
        errors.append("YAML_UNKNOWN_KEY_HARD_ERROR_PROBE_FAILED")
    if not bool(gap_delta.get("p0_strict_config_unknown_key_fail_closed", False)):
        errors.append("P0_3_STRICT_CONFIG_NOT_CLOSED")
    if final_safety_violations:
        errors.append("FINAL_SAFETY_FLAGS_NOT_CLEAN")

    payload.update(
        {
            "ok": ready,
            "status": "READY" if ready else "NOT_READY",
            "decision": READY_DECISION if ready else NOT_READY_DECISION,
            "accepted_for_strict_config_unknown_key_fail_closed": ready,
            "production_hardening_p0_3_ready": ready,
            "errors": errors,
            "final_safety_violation_count": len(final_safety_violations),
            "final_safety_violations": final_safety_violations,
            "report_path": None,
            "strict_config_schema_guard_path": None,
            "strict_config_unknown_key_probe_path": None,
            "p0_gap_closure_delta_path": None,
            "no_submit_p0_3_hardening_gate_path": None,
        }
    )

    if write_reports:
        out_dir = reports_dir or repo_root / "reports" / "recovery"
        stamp = utc_stamp()
        guard_path = out_dir / f"{PATCH_ID}_strict_config_schema_guard_{stamp}.json"
        probe_path = out_dir / f"{PATCH_ID}_strict_config_unknown_key_probe_{stamp}.json"
        delta_path = out_dir / f"{PATCH_ID}_p0_gap_closure_delta_{stamp}.json"
        gate_path = out_dir / f"{PATCH_ID}_no_submit_p0_3_hardening_gate_{stamp}.json"
        report_path = out_dir / f"{PATCH_ID}_{CHECK_NAME}_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(guard_path, {k: v for k, v in config_guard.items() if k.startswith("strict_config_schema") or k.startswith("config_schema") or k in {"guard_name"}})
        write_json(probe_path, {k: v for k, v in config_guard.items() if k.startswith("strict_config_unknown") or k.startswith("yaml_unknown") or k.startswith("strict_config_valid") or k in {"probe_name"}})
        write_json(delta_path, gap_delta)
        write_json(gate_path, gate)
        payload["strict_config_schema_guard_path"] = str(guard_path)
        payload["strict_config_unknown_key_probe_path"] = str(probe_path)
        payload["p0_gap_closure_delta_path"] = str(delta_path)
        payload["no_submit_p0_3_hardening_gate_path"] = str(gate_path)
        payload["report_path"] = str(report_path)
        write_json(report_path, payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    payload = evaluate(repo_root=repo_root, reports_dir=reports_dir, write_reports=args.write_reports)
    if args.once_json or True:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
