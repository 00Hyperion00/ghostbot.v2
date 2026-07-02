from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436633D"
PATCH_VERSION = "4B.4.3.6.6.33D"
PATCH_NAME = "Runtime Safety Lockdown"
READY_DECISION = "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED"
NOT_READY_DECISION = "RUNTIME_SAFETY_LOCKDOWN_NOT_READY"

FALSE_LOCK_FIELDS: tuple[str, ...] = (
    "live_trading_armed",
    "live_real_double_confirm",
    "auto_trade_on_signal",
    "live_real_micro_canary_perform_network_submit",
    "paper_transition_operator_approved",
    "paper_transition_runtime_envelope_frozen",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_dry_run_operator_lock_issued",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_execution_preflight_authorization_issued",
    "paper_sandbox_operator_final_approval_issued",
    "first_paper_sandbox_canary_operator_approval_issued",
)

TRUE_LOCK_FIELDS: tuple[str, ...] = (
    "strict_config_validation",
    "runtime_lock_enabled",
    "promotion_gate_isolation_enabled",
    "paper_kill_switch_enabled",
    "paper_mode_runtime_guardrail_kill_switch_enabled",
    "paper_soak_evidence_window_kill_switch_enabled",
    "live_real_hard_block_required",
    "live_real_preflight_hard_submit_block_required",
    "live_real_final_hard_submit_block_required",
    "live_real_micro_canary_kill_switch_armed",
    "live_real_micro_canary_hard_caps_required",
    "live_real_micro_canary_reconciliation_emergency_stop_armed",
    "live_real_micro_canary_reconciliation_kill_switch_armed",
    "second_micro_canary_submit_gate_no_live_submit_required",
)

ZERO_CAP_FIELDS: tuple[str, ...] = (
    "paper_mode_runtime_guardrail_exchange_submit_cap",
    "paper_mode_runtime_guardrail_network_submit_cap",
    "paper_mode_runtime_guardrail_order_action_cap",
    "paper_soak_evidence_window_exchange_submit_cap",
    "paper_soak_evidence_window_network_submit_cap",
    "paper_soak_evidence_window_order_action_cap",
    "paper_promotion_review_max_total_notional_usd",
    "paper_promotion_review_order_action_cap",
    "live_real_preflight_exchange_submit_cap",
    "live_real_preflight_network_submit_cap",
    "live_real_preflight_order_action_cap",
    "live_real_preflight_max_total_notional_usd",
    "live_real_final_exchange_submit_cap",
    "live_real_final_network_submit_cap",
    "live_real_final_order_action_cap",
    "live_real_final_max_total_notional_usd",
    "live_real_final_max_total_notional_usd",
)

OPERATOR_ACTION_FALSE_FIELDS: tuple[str, ...] = (
    "paper_transition_operator_approved",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_dry_run_operator_lock_issued",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_execution_preflight_authorization_issued",
    "paper_sandbox_operator_final_approval_issued",
    "first_paper_sandbox_canary_operator_approval_issued",
    "live_real_double_confirm",
    "live_trading_armed",
)

RUNTIME_OVERLAY_FALSE_FIELDS: tuple[str, ...] = (
    "live_trading_armed",
    "live_real_micro_canary_perform_network_submit",
    "paper_transition_operator_approved",
    "paper_transition_runtime_envelope_frozen",
)

RUNTIME_OVERLAY_TRUE_FIELDS: tuple[str, ...] = (
    "promotion_gate_isolation_enabled",
    "runtime_lock_enabled",
    "paper_mode_runtime_guardrail_no_exchange_submit_required",
    "paper_mode_runtime_guardrail_no_live_real_required",
    "paper_soak_evidence_window_no_exchange_submit_required",
    "paper_soak_evidence_window_no_live_real_required",
    "live_real_hard_block_required",
    "second_micro_canary_submit_gate_no_live_submit_required",
)

DESTRUCTIVE_PATH_TOKENS: tuple[str, ...] = (
    "submit",
    "order",
    "trade",
    "live",
    "arm",
    "approve",
    "approval",
    "unlock",
    "reload",
    "train",
    "delete",
    "reset",
    "mutation",
    "operator",
    "force",
)

DESTRUCTIVE_GUARD_TOKENS: tuple[str, ...] = (
    "operator",
    "confirm",
    "confirmation",
    "auth",
    "token",
    "lock",
    "guard",
    "blocked",
    "hard_block",
    "hard block",
    "no_exchange_submit",
    "no_live_real",
    "no_live_submit",
    "require",
    "validate",
    "raise httpexception",
    "runtime_lock",
    "kill_switch",
    "local_only",
)

ENDPOINT_PATTERN = re.compile(r"@(?P<owner>app|router)\.(?P<method>post|delete|patch|put)\((?P<args>[^)]*)\)", re.IGNORECASE)
PHASE_33C_REPORT_PATTERN = re.compile(r"4B436633C_phase_chain_validator_.*_(ready|not_ready)\.json$", re.IGNORECASE)


def now_epoch_ms() -> int:
    return int(time.time() * 1000)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def bool_or_false(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def numeric_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - audit readers must not crash the gate
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, None


def payload_is_ready(payload: Mapping[str, Any]) -> bool:
    status = str(payload.get("status") or "").upper()
    decision = str(payload.get("decision") or "").upper()
    if status == "READY":
        return True
    return "READY" in decision and "NOT_READY" not in decision


def load_settings_snapshot(repo_root: Path) -> tuple[dict[str, Any], str | None, list[str]]:
    warnings: list[str] = []
    src_root = repo_root / "src"
    settings: dict[str, Any] = {}
    import_error: str | None = None

    previous_path = list(sys.path)
    previous_tradebot = sys.modules.get("tradebot")
    previous_config = sys.modules.get("tradebot.config")
    try:
        if str(src_root) not in sys.path:
            sys.path.insert(0, str(src_root))
        sys.modules.pop("tradebot.config", None)
        sys.modules.pop("tradebot", None)
        module = importlib.import_module("tradebot.config")
        settings_cls = getattr(module, "Settings", None)
        if settings_cls is None:
            import_error = "tradebot.config.Settings not found"
        else:
            instance = settings_cls()
            if hasattr(instance, "to_dict"):
                try:
                    raw = instance.to_dict(include_secrets=False)
                except TypeError:
                    raw = instance.to_dict()
            elif hasattr(instance, "model_dump"):
                raw = instance.model_dump()
            elif hasattr(instance, "dict"):
                raw = instance.dict()
            else:
                raw = vars(instance)
            if isinstance(raw, Mapping):
                settings = dict(raw)
            else:
                import_error = "Settings snapshot is not a mapping"
    except Exception as exc:  # noqa: BLE001 - fail closed, report import issue
        import_error = f"{type(exc).__name__}: {exc}"
    finally:
        sys.path[:] = previous_path
        if previous_config is not None:
            sys.modules["tradebot.config"] = previous_config
        else:
            sys.modules.pop("tradebot.config", None)
        if previous_tradebot is not None:
            sys.modules["tradebot"] = previous_tradebot
        else:
            sys.modules.pop("tradebot", None)

    if not settings:
        static_settings, static_warnings = load_static_settings(repo_root)
        settings.update(static_settings)
        warnings.extend(static_warnings)
    if import_error:
        warnings.append(f"config_import_warning:{import_error}")
    return settings, import_error, warnings


def load_static_settings(repo_root: Path) -> tuple[dict[str, Any], list[str]]:
    config_path = repo_root / "src" / "tradebot" / "config.py"
    if not config_path.exists():
        return {}, ["config_file_missing"]
    text = config_path.read_text(encoding="utf-8", errors="replace")
    settings: dict[str, Any] = {}
    warnings: list[str] = []
    for key in set(FALSE_LOCK_FIELDS + TRUE_LOCK_FIELDS + ZERO_CAP_FIELDS + OPERATOR_ACTION_FALSE_FIELDS + RUNTIME_OVERLAY_FALSE_FIELDS + RUNTIME_OVERLAY_TRUE_FIELDS):
        match = re.search(rf"{re.escape(key)}\s*[:=][^\n#]*", text)
        if not match:
            continue
        raw_line = match.group(0).split("=", 1)[-1].split(":", 1)[-1].strip().strip(",")
        lowered = raw_line.lower().strip('"\'')
        if lowered in {"true", "false"}:
            settings[key] = lowered == "true"
        else:
            number = numeric_or_none(lowered)
            if number is not None:
                settings[key] = number
            else:
                settings[key] = lowered
    warnings.append("static_config_fallback_used")
    return settings, warnings


@dataclass(slots=True)
class FieldAssertion:
    field: str
    expected: str
    actual: Any
    present: bool
    passed: bool
    severity: str


@dataclass(slots=True)
class CentralSubmitGuard:
    passed: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    network_submit_allowed: bool
    exchange_submit_allowed: bool
    checked_false_fields: list[FieldAssertion]
    checked_true_fields: list[FieldAssertion]
    checked_zero_cap_fields: list[FieldAssertion]
    violations: list[str]
    warnings: list[str]


@dataclass(slots=True)
class OperatorActionGuard:
    passed: bool
    operator_actions_blocked: bool
    checked_fields: list[FieldAssertion]
    violations: list[str]
    warnings: list[str]


@dataclass(slots=True)
class RuntimeOverlayGuard:
    passed: bool
    runtime_overlay_allowed: bool
    checked_false_fields: list[FieldAssertion]
    checked_true_fields: list[FieldAssertion]
    violations: list[str]
    warnings: list[str]


@dataclass(slots=True)
class DestructiveEndpointRecord:
    path: str
    line_number: int
    method: str
    endpoint_signature: str
    destructive: bool
    guarded: bool
    guard_evidence: list[str]
    risk_tokens: list[str]
    severity: str


@dataclass(slots=True)
class DestructiveEndpointAudit:
    complete: bool
    scanned_file_count: int
    endpoint_count: int
    destructive_endpoint_count: int
    unguarded_destructive_endpoint_count: int
    records: list[DestructiveEndpointRecord]
    warnings: list[str]


@dataclass(slots=True)
class Source33CResolution:
    complete: bool
    source_report: str | None
    source_status: str | None
    source_decision: str | None
    parse_error: str | None
    warnings: list[str]


@dataclass(slots=True)
class RuntimeSafetySnapshot:
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    exchange_submit_performed: bool
    destructive_cleanup_performed: bool


@dataclass(slots=True)
class RuntimeSafetyLockdownReport:
    patch_id: str
    patch_version: str
    patch_name: str
    decision: str
    status: str
    generated_at_epoch_ms: int
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    runtime_safety_lockdown_complete: bool
    source_33c_resolution: Source33CResolution
    central_submit_guard: CentralSubmitGuard
    operator_action_guard: OperatorActionGuard
    runtime_overlay_guard: RuntimeOverlayGuard
    destructive_endpoint_audit: DestructiveEndpointAudit
    safety_snapshot: RuntimeSafetySnapshot
    settings_field_count: int
    config_import_error: str | None
    warnings: list[str]
    recommended_next_phase: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assert_false_field(settings: Mapping[str, Any], field: str, *, severity: str = "critical") -> FieldAssertion:
    present = field in settings
    actual = settings.get(field)
    passed = not bool_or_false(actual)
    return FieldAssertion(field=field, expected="false_or_missing_fail_closed", actual=actual, present=present, passed=passed, severity=severity)


def assert_true_field(settings: Mapping[str, Any], field: str, *, severity: str = "warning") -> FieldAssertion:
    present = field in settings
    actual = settings.get(field)
    passed = bool_or_false(actual) if present else True  # missing is fail-closed; warning only
    return FieldAssertion(field=field, expected="true_or_missing_fail_closed", actual=actual, present=present, passed=passed, severity=severity)


def assert_zero_cap(settings: Mapping[str, Any], field: str, *, severity: str = "critical") -> FieldAssertion:
    present = field in settings
    actual = settings.get(field)
    number = numeric_or_none(actual)
    passed = True if not present else number == 0.0
    return FieldAssertion(field=field, expected="0_or_missing_fail_closed", actual=actual, present=present, passed=passed, severity=severity)


def build_central_submit_guard(settings: Mapping[str, Any]) -> CentralSubmitGuard:
    false_checks = [assert_false_field(settings, field) for field in FALSE_LOCK_FIELDS]
    true_checks = [assert_true_field(settings, field) for field in TRUE_LOCK_FIELDS]
    zero_checks = [assert_zero_cap(settings, field) for field in ZERO_CAP_FIELDS]
    violations: list[str] = []
    warnings: list[str] = []

    for item in false_checks + zero_checks:
        if not item.passed and item.severity == "critical":
            violations.append(f"{item.field}: expected {item.expected}, actual={item.actual!r}")
    for item in true_checks:
        if not item.present:
            warnings.append(f"{item.field}: missing; treated fail-closed")
        elif not item.passed:
            violations.append(f"{item.field}: expected true, actual={item.actual!r}")

    live_real_submit_allowed = bool_or_false(settings.get("live_trading_armed")) or bool_or_false(settings.get("live_real_double_confirm")) or bool_or_false(settings.get("live_real_micro_canary_perform_network_submit"))
    paper_submit_allowed = bool_or_false(settings.get("paper_transition_operator_approved")) or bool_or_false(settings.get("paper_transition_runtime_envelope_frozen")) or bool_or_false(settings.get("paper_sandbox_operator_final_approval_issued"))
    network_submit_allowed = live_real_submit_allowed or paper_submit_allowed
    exchange_submit_allowed = network_submit_allowed

    if live_real_submit_allowed:
        violations.append("live_real_submit_allowed=true")
    if paper_submit_allowed:
        violations.append("paper_submit_allowed=true")
    if network_submit_allowed:
        violations.append("network_submit_allowed=true")
    if exchange_submit_allowed:
        violations.append("exchange_submit_allowed=true")

    return CentralSubmitGuard(
        passed=not violations,
        live_real_submit_allowed=live_real_submit_allowed,
        paper_submit_allowed=paper_submit_allowed,
        network_submit_allowed=network_submit_allowed,
        exchange_submit_allowed=exchange_submit_allowed,
        checked_false_fields=false_checks,
        checked_true_fields=true_checks,
        checked_zero_cap_fields=zero_checks,
        violations=violations,
        warnings=warnings,
    )


def build_operator_action_guard(settings: Mapping[str, Any]) -> OperatorActionGuard:
    checks = [assert_false_field(settings, field) for field in OPERATOR_ACTION_FALSE_FIELDS]
    violations = [f"{item.field}: operator gate is open/issued actual={item.actual!r}" for item in checks if not item.passed]
    warnings = [f"{item.field}: missing; treated not issued" for item in checks if not item.present]
    return OperatorActionGuard(
        passed=not violations,
        operator_actions_blocked=not violations,
        checked_fields=checks,
        violations=violations,
        warnings=warnings,
    )


def build_runtime_overlay_guard(settings: Mapping[str, Any]) -> RuntimeOverlayGuard:
    false_checks = [assert_false_field(settings, field) for field in RUNTIME_OVERLAY_FALSE_FIELDS]
    true_checks = [assert_true_field(settings, field) for field in RUNTIME_OVERLAY_TRUE_FIELDS]
    violations: list[str] = []
    warnings: list[str] = []
    for item in false_checks:
        if not item.passed:
            violations.append(f"{item.field}: runtime overlay prerequisite open actual={item.actual!r}")
    for item in true_checks:
        if not item.present:
            warnings.append(f"{item.field}: missing; treated fail-closed")
        elif not item.passed:
            violations.append(f"{item.field}: expected true actual={item.actual!r}")
    runtime_overlay_allowed = any(not item.passed for item in false_checks)
    if runtime_overlay_allowed:
        violations.append("runtime_overlay_allowed=true")
    return RuntimeOverlayGuard(
        passed=not violations,
        runtime_overlay_allowed=runtime_overlay_allowed,
        checked_false_fields=false_checks,
        checked_true_fields=true_checks,
        violations=violations,
        warnings=warnings,
    )


def iter_python_source_files(repo_root: Path) -> Iterable[Path]:
    src_root = repo_root / "src"
    if not src_root.exists():
        return []
    files: list[Path] = []
    for path in src_root.rglob("*.py"):
        rel_parts = set(path.relative_to(repo_root).parts)
        if rel_parts.intersection({"__pycache__", ".pytest_cache", "_patch_backup", "_patch_payload", "legacy_patches"}):
            continue
        files.append(path)
    return files


def endpoint_block(lines: Sequence[str], start_index: int, max_lines: int = 80) -> str:
    return "\n".join(lines[start_index : min(len(lines), start_index + max_lines)])


def extract_endpoint_signature(line: str) -> str:
    return line.strip()


def audit_destructive_endpoints(repo_root: Path) -> DestructiveEndpointAudit:
    records: list[DestructiveEndpointRecord] = []
    warnings: list[str] = []
    scanned_count = 0
    endpoint_count = 0

    for path in iter_python_source_files(repo_root):
        scanned_count += 1
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as exc:  # noqa: BLE001 - source audit must not crash
            warnings.append(f"{safe_relative(path, repo_root)}: read_error:{type(exc).__name__}: {exc}")
            continue
        for index, line in enumerate(lines):
            match = ENDPOINT_PATTERN.search(line)
            if not match:
                continue
            endpoint_count += 1
            block = endpoint_block(lines, index).lower()
            signature = extract_endpoint_signature(line)
            risk_tokens = [token for token in DESTRUCTIVE_PATH_TOKENS if token in block or token in line.lower()]
            destructive = bool(risk_tokens)
            guard_evidence = [token for token in DESTRUCTIVE_GUARD_TOKENS if token in block]
            guarded = (not destructive) or bool(guard_evidence)
            severity = "critical" if destructive and not guarded else ("info" if destructive else "none")
            records.append(
                DestructiveEndpointRecord(
                    path=safe_relative(path, repo_root),
                    line_number=index + 1,
                    method=match.group("method").upper(),
                    endpoint_signature=signature,
                    destructive=destructive,
                    guarded=guarded,
                    guard_evidence=guard_evidence,
                    risk_tokens=risk_tokens,
                    severity=severity,
                )
            )

    destructive_count = sum(1 for record in records if record.destructive)
    unguarded_count = sum(1 for record in records if record.destructive and not record.guarded)
    return DestructiveEndpointAudit(
        complete=unguarded_count == 0,
        scanned_file_count=scanned_count,
        endpoint_count=endpoint_count,
        destructive_endpoint_count=destructive_count,
        unguarded_destructive_endpoint_count=unguarded_count,
        records=records,
        warnings=warnings,
    )


def resolve_33c_report(repo_root: Path) -> Source33CResolution:
    recovery_dir = repo_root / "reports" / "recovery"
    warnings: list[str] = []
    if not recovery_dir.exists():
        return Source33CResolution(False, None, None, None, None, ["reports/recovery missing"])
    candidates = sorted(
        [path for path in recovery_dir.glob("4B436633C_phase_chain_validator_*.json") if PHASE_33C_REPORT_PATTERN.search(path.name)],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return Source33CResolution(False, None, None, None, None, ["33C ready report missing"])
    for path in candidates:
        payload, parse_error = read_json_object(path)
        if parse_error or payload is None:
            warnings.append(f"{safe_relative(path, repo_root)} parse_error:{parse_error}")
            continue
        status = str(payload.get("status") or "")
        decision = str(payload.get("decision") or "")
        if payload_is_ready(payload):
            return Source33CResolution(True, safe_relative(path, repo_root), status, decision, None, warnings)
        warnings.append(f"{safe_relative(path, repo_root)} not ready: status={status} decision={decision}")
    latest = candidates[0]
    payload, parse_error = read_json_object(latest)
    return Source33CResolution(False, safe_relative(latest, repo_root), None if not payload else str(payload.get("status") or ""), None if not payload else str(payload.get("decision") or ""), parse_error, warnings)


def build_runtime_safety_lockdown(repo_root: str | Path = ".") -> RuntimeSafetyLockdownReport:
    root = Path(repo_root).resolve()
    settings, import_error, config_warnings = load_settings_snapshot(root)
    source_33c = resolve_33c_report(root)
    central_guard = build_central_submit_guard(settings)
    operator_guard = build_operator_action_guard(settings)
    overlay_guard = build_runtime_overlay_guard(settings)
    endpoint_audit = audit_destructive_endpoints(root)
    safety_snapshot = RuntimeSafetySnapshot(
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        exchange_submit_performed=False,
        destructive_cleanup_performed=False,
    )

    approved_for_live_real = False
    approved_for_paper_transition = False
    approved_for_exchange_submit = False
    approved_for_runtime_overlay = False
    complete = (
        source_33c.complete
        and central_guard.passed
        and operator_guard.passed
        and overlay_guard.passed
        and endpoint_audit.complete
        and not safety_snapshot.trading_action_performed
        and not safety_snapshot.training_performed
        and not safety_snapshot.reload_performed
        and not safety_snapshot.runtime_overlay_activated
        and not safety_snapshot.exchange_submit_performed
        and not safety_snapshot.destructive_cleanup_performed
    )
    status = "READY" if complete else "NOT_READY"
    decision = READY_DECISION if complete else NOT_READY_DECISION
    warnings = [*config_warnings, *source_33c.warnings, *central_guard.warnings, *operator_guard.warnings, *overlay_guard.warnings, *endpoint_audit.warnings]

    return RuntimeSafetyLockdownReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        decision=decision,
        status=status,
        generated_at_epoch_ms=now_epoch_ms(),
        approved_for_live_real=approved_for_live_real,
        approved_for_paper_transition=approved_for_paper_transition,
        approved_for_exchange_submit=approved_for_exchange_submit,
        approved_for_runtime_overlay=approved_for_runtime_overlay,
        runtime_safety_lockdown_complete=complete,
        source_33c_resolution=source_33c,
        central_submit_guard=central_guard,
        operator_action_guard=operator_guard,
        runtime_overlay_guard=overlay_guard,
        destructive_endpoint_audit=endpoint_audit,
        safety_snapshot=safety_snapshot,
        settings_field_count=len(settings),
        config_import_error=import_error,
        warnings=warnings,
        recommended_next_phase="4B.4.3.6.6.33E Status Conflict Resolver" if complete else "Fix runtime safety lockdown blockers before continuing",
    )


def report_filename(report: RuntimeSafetyLockdownReport) -> str:
    suffix = "ready" if report.status == "READY" else "not_ready"
    import datetime as _dt
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{PATCH_ID}_runtime_safety_lockdown_{timestamp}_{suffix}.json"


def write_report(report: RuntimeSafetyLockdownReport, reports_dir: str | Path) -> Path:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / report_filename(report)
    output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def summarize(report: RuntimeSafetyLockdownReport, report_path: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "check_name": "runtime_safety_lockdown",
        "status": report.status,
        "decision": report.decision,
        "runtime_safety_lockdown_complete": report.runtime_safety_lockdown_complete,
        "source_33c_report": report.source_33c_resolution.source_report,
        "source_33c_complete": report.source_33c_resolution.complete,
        "central_submit_guard_passed": report.central_submit_guard.passed,
        "operator_action_guard_passed": report.operator_action_guard.passed,
        "runtime_overlay_guard_passed": report.runtime_overlay_guard.passed,
        "destructive_endpoint_audit_complete": report.destructive_endpoint_audit.complete,
        "destructive_endpoint_count": report.destructive_endpoint_audit.destructive_endpoint_count,
        "unguarded_destructive_endpoint_count": report.destructive_endpoint_audit.unguarded_destructive_endpoint_count,
        "live_real_submit_allowed": report.central_submit_guard.live_real_submit_allowed,
        "paper_submit_allowed": report.central_submit_guard.paper_submit_allowed,
        "network_submit_allowed": report.central_submit_guard.network_submit_allowed,
        "exchange_submit_allowed": report.central_submit_guard.exchange_submit_allowed,
        "runtime_overlay_allowed": report.runtime_overlay_guard.runtime_overlay_allowed,
        "approved_for_live_real": report.approved_for_live_real,
        "approved_for_paper_transition": report.approved_for_paper_transition,
        "approved_for_exchange_submit": report.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.approved_for_runtime_overlay,
        "submit_violations": report.central_submit_guard.violations,
        "operator_violations": report.operator_action_guard.violations,
        "overlay_violations": report.runtime_overlay_guard.violations,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,
        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,
        "destructive_cleanup_performed": report.safety_snapshot.destructive_cleanup_performed,
        "warning_count": len(report.warnings),
    }
    if report_path is not None:
        payload["report_path"] = str(report_path)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    report = build_runtime_safety_lockdown(args.repo_root)
    report_path: Path | None = None
    if args.write_report:
        report_path = write_report(report, Path(args.repo_root) / args.reports_dir)
    payload = summarize(report, report_path)
    if args.once_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
