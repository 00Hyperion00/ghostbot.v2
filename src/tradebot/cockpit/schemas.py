from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

OPERATOR_COCKPIT_CONTRACT_VERSION = "4B.4.3.6.6.33A"
OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION = "4B.4.3.6.6.33B"
OPERATOR_COCKPIT_RUNTIME_HARDENING_ENABLED = True
OPERATOR_COCKPIT_SECURITY_GATE_VERSION = "4B.4.3.6.6.33C"
OPERATOR_COCKPIT_SECURITY_GATE_ENABLED = True
OPERATOR_COCKPIT_UX_HEALTH_VERSION = "4B.4.3.6.6.33D"
OPERATOR_COCKPIT_UX_HEALTH_ENABLED = True
OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION = "4B.4.3.6.6.33E"
OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_ENABLED = True
OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION = "4B.4.3.6.6.33F"
OPERATOR_COCKPIT_RISK_RECONCILIATION_ENABLED = True
OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION = "4B.4.3.6.6.33G"
OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_ENABLED = True
OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION = "4B.4.3.6.6.33H"
OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_ENABLED = True
OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION = "4B.4.3.6.6.33I"
OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_ENABLED = True
OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION = "4B.4.3.6.6.33J"
OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_ENABLED = True
OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION = "4B.4.3.6.6.33K"
OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_ENABLED = True
OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION = "4B.4.3.6.6.33L"
OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_ENABLED = True
OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION = "4B.4.3.6.6.33M"
OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_ENABLED = True
OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION = "4B.4.3.6.6.34"
OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_ENABLED = True


def utc_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True)
class CockpitActionResult:
    ok: bool
    action: str
    message: str
    data: dict[str, Any] | None = None
    contract_version: str = OPERATOR_COCKPIT_CONTRACT_VERSION
    runtime_hardening_version: str = OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION
    security_gate_version: str = OPERATOR_COCKPIT_SECURITY_GATE_VERSION
    ux_health_version: str = OPERATOR_COCKPIT_UX_HEALTH_VERSION
    action_audit_runtime_lock_version: str = OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION
    risk_reconciliation_version: str = OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION
    reconciliation_execution_version: str = OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION
    reconciliation_decision_apply_version: str = OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION
    engine_position_recovery_gate_version: str = OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION
    recovery_plan_apply_verification_gate_version: str = OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION
    external_recovery_evidence_gate_version: str = OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION
    exchange_environment_source_gate_version: str = OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION
    engine_status_balance_cache_reconciliation_version: str = OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION
    demo_entry_execution_control_version: str = OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data"] = self.data or {}
        return payload


@dataclass(frozen=True, slots=True)
class CockpitSystemSnapshot:
    pid: int
    uptime_sec: float
    heartbeat_age_ms: int
    process_started_at_ms: int
    now_ms: int
    engine_running: bool = False
    engine_started_at_ms: int | None = None
    engine_uptime_sec: float | None = None
    cpu_percent: float | None = None
    memory_rss_mb: float | None = None
    memory_percent: float | None = None
    psutil_available: bool = False
    contract_version: str = OPERATOR_COCKPIT_CONTRACT_VERSION
    runtime_hardening_version: str = OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION
    security_gate_version: str = OPERATOR_COCKPIT_SECURITY_GATE_VERSION
    ux_health_version: str = OPERATOR_COCKPIT_UX_HEALTH_VERSION
    action_audit_runtime_lock_version: str = OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION
    risk_reconciliation_version: str = OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION
    reconciliation_execution_version: str = OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION
    reconciliation_decision_apply_version: str = OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION
    engine_position_recovery_gate_version: str = OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION
    recovery_plan_apply_verification_gate_version: str = OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION
    external_recovery_evidence_gate_version: str = OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION
    exchange_environment_source_gate_version: str = OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION
    engine_status_balance_cache_reconciliation_version: str = OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION
    demo_entry_execution_control_version: str = OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
