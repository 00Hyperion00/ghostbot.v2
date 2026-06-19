from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29A"
PRODUCTION_HARDENING_TRACK = "PRODUCTION_HARDENING_P0"
PROMOTION_GATE_ISOLATION_VERSION = CONTRACT_VERSION
DEFAULT_ROUND_TRIP_COST_BPS = 24.0
RUNTIME_LOCK_CONTRACT_VERSION = CONTRACT_VERSION

PROMOTION_TARGETS = frozenset({
    "runtime_overlay_activation",
    "parameter_relaxation",
    "paper_candidate",
    "live_real",
    "training_reload",
    "order_path",
})


@dataclass(frozen=True, slots=True)
class RuntimeLockHandle:
    path: str
    identity: str
    acquired_at_epoch_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductionHardeningStatus:
    contract_version: str
    install_contract_ready: bool
    strict_config_ready: bool
    api_auth_controls_ready: bool
    sqlite_audit_baseline_ready: bool
    runtime_lock_ready: bool
    fee_slippage_baseline_ready: bool
    promotion_gate_isolation_ready: bool
    report_commit_policy_ready: bool

    @property
    def ready(self) -> bool:
        return all(asdict(self).get(key) is True for key in asdict(self) if key != "contract_version")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ready"] = self.ready
        return payload


def _bool_attr(settings: Any, name: str, default: bool) -> bool:
    return bool(getattr(settings, name, default))


def _float_attr(settings: Any, name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def build_production_hardening_status(settings: Any | None = None) -> ProductionHardeningStatus:
    settings = settings or object()
    return ProductionHardeningStatus(
        contract_version=CONTRACT_VERSION,
        install_contract_ready=True,
        strict_config_ready=_bool_attr(settings, "strict_config_validation", True),
        api_auth_controls_ready=hasattr(settings, "api_auth_enabled") and hasattr(settings, "destructive_action_confirmation_required"),
        sqlite_audit_baseline_ready=_bool_attr(settings, "sqlite_wal_enabled", True),
        runtime_lock_ready=_bool_attr(settings, "runtime_lock_enabled", True),
        fee_slippage_baseline_ready=_float_attr(settings, "fee_slippage_baseline_bps", DEFAULT_ROUND_TRIP_COST_BPS) > 0,
        promotion_gate_isolation_ready=_bool_attr(settings, "promotion_gate_isolation_enabled", True),
        report_commit_policy_ready=True,
    )


def build_production_hardening_snapshot(settings: Any | None = None) -> dict[str, Any]:
    status = build_production_hardening_status(settings)
    return {
        "contract_version": CONTRACT_VERSION,
        "track": PRODUCTION_HARDENING_TRACK,
        "read_only": True,
        "ok": True,
        "status": status.to_dict(),
        "promotion_gate_isolation": {
            "version": PROMOTION_GATE_ISOLATION_VERSION,
            "production_readiness_not_inferred_from_hypothesis_performance": True,
            "hypothesis_outputs_cannot_enable_runtime_paper_live_or_order_path": True,
            "requires_independent_production_hardening_gate": True,
        },
        "mutations": {
            "strategy_parameter_mutation_performed": False,
            "runtime_overlay_activation_performed": False,
            "scheduler_mutation_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
            "paper_live_order_enablement_performed": False,
        },
    }


def evaluate_promotion_gate(
    *,
    target: str,
    hypothesis_payload: dict[str, Any] | None = None,
    production_hardening_complete: bool = False,
    explicit_operator_approval: bool = False,
    independent_release_gate_passed: bool = False,
) -> dict[str, Any]:
    normalized_target = str(target or "").strip()
    reasons: list[str] = []
    if normalized_target not in PROMOTION_TARGETS:
        reasons.append("PROMOTION_TARGET_UNKNOWN")
    if hypothesis_payload:
        reasons.append("HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS")
    if not production_hardening_complete:
        reasons.append("PRODUCTION_HARDENING_P0_NOT_COMPLETE")
    if not explicit_operator_approval:
        reasons.append("EXPLICIT_OPERATOR_APPROVAL_MISSING")
    if not independent_release_gate_passed:
        reasons.append("INDEPENDENT_RELEASE_GATE_NOT_PASSED")
    allowed = not reasons
    return {
        "contract_version": CONTRACT_VERSION,
        "gate": "PROMOTION_GATE_ISOLATION",
        "target": normalized_target or "UNKNOWN",
        "allowed": allowed,
        "approved_for_runtime_overlay_activation": False if not allowed else normalized_target == "runtime_overlay_activation",
        "approved_for_parameter_relaxation": False if not allowed else normalized_target == "parameter_relaxation",
        "approved_for_paper_candidate": False if not allowed else normalized_target == "paper_candidate",
        "approved_for_live_real": False if not allowed else normalized_target == "live_real",
        "approved_for_training_reload": False if not allowed else normalized_target == "training_reload",
        "approved_for_order_path": False if not allowed else normalized_target == "order_path",
        "reason_codes": reasons,
        "hypothesis_payload_present": bool(hypothesis_payload),
        "production_readiness_not_inferred_from_hypothesis_performance": True,
    }


def acquire_runtime_lock(path: str | Path, *, identity: str, stale_after_seconds: int = 0) -> RuntimeLockHandle:
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now_ms = int(time.time() * 1000)
    payload = {"contract_version": CONTRACT_VERSION, "identity": str(identity), "acquired_at_epoch_ms": now_ms, "pid": os.getpid()}
    if lock_path.exists():
        if stale_after_seconds > 0:
            age = time.time() - lock_path.stat().st_mtime
            if age > stale_after_seconds:
                lock_path.unlink(missing_ok=True)
            else:
                raise RuntimeError("RUNTIME_LOCK_ALREADY_HELD")
        else:
            raise RuntimeError("RUNTIME_LOCK_ALREADY_HELD")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    finally:
        os.close(fd)
    return RuntimeLockHandle(path=str(lock_path), identity=str(identity), acquired_at_epoch_ms=now_ms)


def release_runtime_lock(handle: RuntimeLockHandle | dict[str, Any]) -> None:
    path = Path(handle.path if isinstance(handle, RuntimeLockHandle) else str(handle.get("path")))
    if path.exists():
        path.unlink()


def canonical_evidence_commit_decision(path: str | Path) -> dict[str, Any]:
    text = Path(path).as_posix().replace("\\", "/")
    allowed = (
        text.startswith("docs/")
        or text.startswith("tests/")
        or text.startswith("src/")
        or text.startswith("tools/")
        or text.startswith("reports/hyp006_r1_canonical/4B436628G_H8_")
        or text.startswith("reports/hyp006_r1_canonical/4B436629A_")
    )
    if "_patch_backup" in text or "_patch_payload" in text or text.endswith(".pyc"):
        allowed = False
    return {
        "contract_version": CONTRACT_VERSION,
        "path": text,
        "canonical_evidence_commit_allowed": bool(allowed),
        "reason_code": "CANONICAL_EVIDENCE_ALLOWED" if allowed else "TRANSIENT_OR_NON_CANONICAL_REPORT_BLOCKED",
    }
