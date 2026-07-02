from __future__ import annotations

import asyncio
import inspect
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:  # optional dependency; cockpit remains functional without psutil
    import psutil  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - platform/optional dependency fallback
    psutil = None  # type: ignore[assignment]

from ..config import Settings
from ..engine import TradeBotEngine
from ..persistence import SQLiteStore
from ..production_hardening import RuntimeLockHandle, acquire_runtime_lock, release_runtime_lock
from .schemas import (
    CockpitActionResult,
    CockpitSystemSnapshot,
    OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
    OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
    OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
    OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
    OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION,
    OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
    OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
    OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
    OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
    OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
    OPERATOR_COCKPIT_CONTRACT_VERSION,
    OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
    OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
    OPERATOR_COCKPIT_UX_HEALTH_VERSION,
    utc_ms,
)
from .security import build_security_snapshot, fetch_recent_operator_actions

_KNOWN_QUOTE_ASSETS = (
    "FDUSD",
    "USDT",
    "USDC",
    "BUSD",
    "TUSD",
    "TRY",
    "BTC",
    "ETH",
    "BNB",
)
DEFAULT_RUNTIME_LOCK_STALE_AFTER_SECONDS = 900


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            result = to_dict()
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_assets(symbol: str, balances: dict[str, Any]) -> tuple[str, str]:
    normalized = str(symbol or "").strip().upper()
    for quote in sorted(_KNOWN_QUOTE_ASSETS, key=len, reverse=True):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    for asset, raw in balances.items():
        asset_text = str(asset or "").strip().upper()
        if asset_text and asset_text not in _KNOWN_QUOTE_ASSETS:
            data = _as_dict(raw)
            if _float_value(data.get("free")) + _float_value(data.get("locked")) > 0:
                return asset_text, "UNKNOWN"
    return "UNKNOWN", "UNKNOWN"


def _find_recent_orphan_recovery(logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in logs:
        code = str(item.get("code") or "").upper()
        data = _as_dict(item.get("data"))
        if code == "RECOVERY_RECONCILE_COMPLETED" and str(data.get("position_action") or "").upper() == "CLEARED_ORPHAN_LOCAL_POSITION":
            return item
    return None


def _runtime_lock_path(settings: Any) -> Path:
    raw = getattr(settings, "runtime_lock_path", ".tradebot/runtime.lock") or ".tradebot/runtime.lock"
    path = Path(str(raw))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _pid_is_alive(pid: Any) -> bool | None:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return None
    if pid_int <= 0:
        return None
    if pid_int == os.getpid():
        return True
    if psutil is not None:
        try:
            return bool(psutil.pid_exists(pid_int))
        except Exception:
            return None
    if os.name != "nt":
        try:
            os.kill(pid_int, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return None
    return None


def inspect_runtime_lock(settings: Any, handle: RuntimeLockHandle | None = None) -> dict[str, Any]:
    """Return read-only runtime lock diagnostics for duplicate/stale cockpit visibility."""

    path = Path(handle.path) if handle is not None else _runtime_lock_path(settings)
    now = time.time()
    payload: dict[str, Any] = {}
    raw_text = ""
    parse_error: str | None = None
    exists = path.exists()
    stat_size: int | None = None
    mtime_epoch: float | None = None
    mtime_epoch_ms: int | None = None
    age_seconds: float | None = None
    if exists:
        try:
            stat = path.stat()
            stat_size = int(stat.st_size)
            mtime_epoch = float(stat.st_mtime)
            mtime_epoch_ms = int(mtime_epoch * 1000)
            age_seconds = max(now - mtime_epoch, 0.0)
            raw_text = path.read_text(encoding="utf-8", errors="replace")[:2048]
            try:
                loaded = json.loads(raw_text) if raw_text.strip() else {}
                payload = loaded if isinstance(loaded, dict) else {}
            except Exception as exc:
                parse_error = str(exc)
        except Exception as exc:
            parse_error = str(exc)
    payload_pid = payload.get("pid")
    pid_alive = _pid_is_alive(payload_pid)
    owned_by_current_process = bool(handle is not None) or payload_pid == os.getpid()
    try:
        threshold = int(getattr(settings, "runtime_lock_stale_after_seconds", DEFAULT_RUNTIME_LOCK_STALE_AFTER_SECONDS) or DEFAULT_RUNTIME_LOCK_STALE_AFTER_SECONDS)
    except (TypeError, ValueError):
        threshold = DEFAULT_RUNTIME_LOCK_STALE_AFTER_SECONDS
    stale_by_age = bool(exists and age_seconds is not None and threshold > 0 and age_seconds > threshold)
    stale_by_dead_pid = bool(exists and payload_pid is not None and pid_alive is False)
    stale_reclaim_safe = bool(exists and not owned_by_current_process and (stale_by_dead_pid or (stale_by_age and pid_alive is not True)))
    duplicate_instance_blocked = bool(exists and not owned_by_current_process and pid_alive is True)
    reason_codes: list[str] = []
    if exists:
        reason_codes.append("RUNTIME_LOCK_FILE_PRESENT")
    if owned_by_current_process:
        reason_codes.append("RUNTIME_LOCK_OWNED_BY_CURRENT_PROCESS")
    if duplicate_instance_blocked:
        reason_codes.append("DUPLICATE_COCKPIT_INSTANCE_BLOCKED")
    if stale_by_dead_pid:
        reason_codes.append("STALE_RUNTIME_LOCK_DEAD_PID")
    if stale_by_age:
        reason_codes.append("STALE_RUNTIME_LOCK_BY_AGE")
    if stale_reclaim_safe:
        reason_codes.append("STALE_RUNTIME_LOCK_RECLAIM_AVAILABLE")
    if parse_error:
        reason_codes.append("RUNTIME_LOCK_PAYLOAD_PARSE_WARNING")
    return {
        "contract_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
        "enabled": bool(getattr(settings, "runtime_lock_enabled", True)),
        "path": str(path),
        "exists": bool(exists),
        "size_bytes": stat_size,
        "mtime_epoch_ms": mtime_epoch_ms,
        "age_seconds": None if age_seconds is None else round(age_seconds, 3),
        "stale_after_seconds": threshold,
        "payload": payload,
        "raw_preview": raw_text,
        "parse_error": parse_error,
        "pid": payload_pid,
        "pid_alive": pid_alive,
        "identity": payload.get("identity"),
        "acquired_at_epoch_ms": payload.get("acquired_at_epoch_ms"),
        "owned_by_current_process": owned_by_current_process,
        "held_by_current_process": bool(handle is not None),
        "duplicate_instance_blocked": duplicate_instance_blocked,
        "stale_by_age": stale_by_age,
        "stale_by_dead_pid": stale_by_dead_pid,
        "stale_reclaim_safe": stale_reclaim_safe,
        "clear_confirmation": "CONFIRM_CLEAR_STALE_RUNTIME_LOCK",
        "reason_codes": reason_codes,
    }


def build_runtime_awareness_snapshot(status: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive cockpit-only balance/position awareness without mutating engine state."""

    status = status if isinstance(status, dict) else {}
    balances = _as_dict(status.get("balances"))
    config_safety = _as_dict(status.get("config_safety_snapshot"))
    symbol = str(status.get("symbol") or config_safety.get("symbol") or "").upper()
    base_asset, quote_asset = _infer_assets(symbol, balances)
    base_balance = _as_dict(balances.get(base_asset, {})) if base_asset != "UNKNOWN" else {}
    base_free = _float_value(base_balance.get("free"))
    base_locked = _float_value(base_balance.get("locked"))
    base_dust = _float_value(base_balance.get("dust"))
    tradable_base = max(base_free - base_dust, 0.0)

    position = _as_dict(status.get("position_snapshot"))
    pending = _as_dict(status.get("pending_snapshot"))
    position_present = bool(position.get("present", False))
    pending_present = bool(pending.get("present", False))
    base_balance_present = tradable_base > 0
    not_tracked = base_balance_present and not position_present
    orphan_log = _find_recent_orphan_recovery(logs)
    orphan_detected = orphan_log is not None
    active_anomaly_code = str(status.get("active_anomaly_code") or "").strip()

    reason_codes: list[str] = []
    if not_tracked:
        reason_codes.append("BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED")
    if orphan_detected:
        reason_codes.append("ORPHAN_LOCAL_POSITION_RECOVERY_DETECTED")
    if active_anomaly_code:
        reason_codes.append(f"ACTIVE_ANOMALY_{active_anomaly_code}")

    if active_anomaly_code or (orphan_detected and not_tracked):
        risk_badge = "RED"
        banner_title = "Runtime position mismatch requires operator review"
        banner_message = "Tradable base balance exists while runtime position is not tracked after orphan recovery. Do not authorize new entry until reconciliation is reviewed."
        recommended_action = "REVIEW_RECOVERY_LOGS_AND_BALANCE_SYNC_BEFORE_ENTRY"
    elif not_tracked or orphan_detected:
        risk_badge = "YELLOW"
        banner_title = "Base balance awareness warning"
        banner_message = "Base asset balance is present while runtime position may not be tracked. Confirm whether this is intentional inventory or leftover exposure."
        recommended_action = "BALANCE_SYNC_AND_OPERATOR_REVIEW"
    else:
        risk_badge = "GREEN"
        banner_title = "Runtime inventory tracking normal"
        banner_message = "No base-balance / position-tracking mismatch detected in the current cockpit snapshot."
        recommended_action = "NONE"

    return {
        "contract_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
        "runtime_hardening_enabled": True,
        "risk_badge": risk_badge,
        "banner_title": banner_title,
        "banner_message": banner_message,
        "recommended_action": recommended_action,
        "reason_codes": reason_codes,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "base_free": base_free,
        "base_locked": base_locked,
        "base_dust": base_dust,
        "tradable_base": tradable_base,
        "base_balance_present": bool(base_balance_present),
        "position_present": bool(position_present),
        "pending_present": bool(pending_present),
        "base_balance_present_position_not_tracked": bool(not_tracked),
        "orphan_local_position_recovery_detected": bool(orphan_detected),
        "active_anomaly_code": active_anomaly_code or None,
        "auto_entry_risk_attention_required": risk_badge != "GREEN",
        "orphan_recovery_log_ts": orphan_log.get("ts") if orphan_log else None,
    }


def summarize_operator_actions(actions: list[dict[str, Any]]) -> dict[str, Any]:
    by_outcome: dict[str, int] = {}
    by_action: dict[str, int] = {}
    latest_ts: int | None = None
    for item in actions:
        outcome = str(item.get("outcome") or "UNKNOWN")
        action = str(item.get("action") or "UNKNOWN")
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        by_action[action] = by_action.get(action, 0) + 1
        try:
            ts = int(item.get("ts") or 0)
            latest_ts = max(latest_ts or 0, ts) if ts else latest_ts
        except Exception:
            pass
    return {
        "contract_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
        "enabled": True,
        "total_returned": len(actions),
        "latest_ts": latest_ts,
        "by_outcome": by_outcome,
        "by_action": by_action,
        "has_blocked_actions": any(key.startswith("BLOCKED") for key in by_outcome),
        "has_failed_actions": any("FAILED" in key for key in by_outcome),
    }


def _reconciliation_key(settings: Any) -> str:
    symbol = str(getattr(settings, "symbol", "UNKNOWN") or "UNKNOWN").upper()
    return f"cockpit:risk_reconciliation_ack:{symbol}"


def _reconciliation_decision_key(settings: Any) -> str:
    symbol = str(getattr(settings, "symbol", "UNKNOWN") or "UNKNOWN").upper()
    return f"cockpit:risk_reconciliation_decision:{symbol}"


def _safe_store_get_json(store: Any, key: str, default: Any = None) -> Any:
    try:
        return store.get_json(key, default)
    except Exception:
        return default


def _safe_store_set_json(store: Any, key: str, value: Any) -> bool:
    try:
        store.set_json(key, value)
        return True
    except Exception:
        return False


def build_balance_review_snapshot(status: dict[str, Any], runtime_awareness: dict[str, Any]) -> dict[str, Any]:
    status = status if isinstance(status, dict) else {}
    balances = _as_dict(status.get("balances"))
    base_asset = str(runtime_awareness.get("base_asset") or "UNKNOWN")
    quote_asset = str(runtime_awareness.get("quote_asset") or "UNKNOWN")
    base_balance = _as_dict(balances.get(base_asset, {})) if base_asset != "UNKNOWN" else {}
    quote_balance = _as_dict(balances.get(quote_asset, {})) if quote_asset != "UNKNOWN" else {}
    return {
        "contract_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
        "read_only": True,
        "review_required": bool(runtime_awareness.get("auto_entry_risk_attention_required", False)),
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "base": {
            "free": _float_value(base_balance.get("free"), _float_value(runtime_awareness.get("base_free"))),
            "locked": _float_value(base_balance.get("locked"), _float_value(runtime_awareness.get("base_locked"))),
            "dust": _float_value(base_balance.get("dust"), _float_value(runtime_awareness.get("base_dust"))),
            "tradable": _float_value(runtime_awareness.get("tradable_base")),
            "source": "engine_status_balances",
        },
        "quote": {
            "free": _float_value(quote_balance.get("free")),
            "locked": _float_value(quote_balance.get("locked")),
            "source": "engine_status_balances",
        },
        "position_present": bool(runtime_awareness.get("position_present", False)),
        "pending_present": bool(runtime_awareness.get("pending_present", False)),
        "base_balance_present_position_not_tracked": bool(runtime_awareness.get("base_balance_present_position_not_tracked", False)),
        "reason_codes": list(runtime_awareness.get("reason_codes") or []),
    }


def build_risk_reconciliation_snapshot(*, status: dict[str, Any], runtime_awareness: dict[str, Any], balance_review: dict[str, Any], acknowledgement: dict[str, Any] | None) -> dict[str, Any]:
    mismatch_active = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False))
    orphan_active = bool(runtime_awareness.get("orphan_local_position_recovery_detected", False))
    red_badge = str(runtime_awareness.get("risk_badge") or "").upper() == "RED"
    review_required = bool(mismatch_active or orphan_active or red_badge)
    acknowledgement_present = bool(acknowledgement)
    reconciled = bool(not review_required)
    reason_codes: list[str] = []
    if mismatch_active:
        reason_codes.append("BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED")
    if orphan_active:
        reason_codes.append("ORPHAN_RECOVERY_REQUIRES_RECONCILIATION")
    if red_badge:
        reason_codes.append("RED_RISK_BADGE_RECONCILIATION_REQUIRED")
    if acknowledgement_present and review_required:
        reason_codes.append("ACKNOWLEDGED_BUT_NOT_RECONCILED")
    if not review_required:
        reason_codes.append("RISK_RECONCILIATION_NOT_REQUIRED")
    return {
        "contract_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
        "enabled": True,
        "read_only_balance_review": True,
        "wizard_enabled": True,
        "manual_position_acknowledgement_gate_enabled": True,
        "entry_block_until_reconciled": True,
        "status": "REVIEW_REQUIRED" if review_required else "RECONCILED",
        "review_required": review_required,
        "mismatch_active": mismatch_active,
        "orphan_recovery_detected": orphan_active,
        "risk_badge": runtime_awareness.get("risk_badge"),
        "acknowledgement_present": acknowledgement_present,
        "acknowledgement": acknowledgement or {},
        "acknowledgement_allows_entry": False,
        "reconciled": reconciled,
        "entry_blocked_until_reconciled": bool(review_required),
        "force_buy_blocked": bool(review_required),
        "manual_resolution_required": bool(review_required),
        "recommended_action": "REVIEW_BALANCE_AND_RESOLVE_POSITION_TRACKING_BEFORE_ENTRY" if review_required else "NONE",
        "wizard_steps": [
            {"step": 1, "name": "Read-only balance review", "complete": bool(balance_review)},
            {"step": 2, "name": "Confirm whether base inventory is intentional", "complete": acknowledgement_present},
            {"step": 3, "name": "Resolve runtime position tracking mismatch", "complete": reconciled},
            {"step": 4, "name": "Re-check entry guard before any BUY", "complete": reconciled},
        ],
        "reason_codes": reason_codes,
    }


def build_tracked_position_adoption_candidate(status: dict[str, Any], runtime_awareness: dict[str, Any], balance_review: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only adoption candidate; it does not mutate engine/runtime position state."""

    position = _as_dict(status.get("position_snapshot"))
    mark_price = _float_value(position.get("mark_price"), _float_value(status.get("mark_price")))
    qty = _float_value(runtime_awareness.get("tradable_base"))
    notional = qty * mark_price if qty > 0 and mark_price > 0 else None
    candidate_available = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False) and qty > 0)
    reason_codes: list[str] = []
    if candidate_available:
        reason_codes.append("TRACKED_POSITION_ADOPTION_CANDIDATE_AVAILABLE")
    else:
        reason_codes.append("TRACKED_POSITION_ADOPTION_CANDIDATE_NOT_AVAILABLE")
    if bool(position.get("present", False)):
        reason_codes.append("RUNTIME_POSITION_ALREADY_PRESENT")
    return {
        "contract_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
        "read_only": True,
        "candidate_available": candidate_available,
        "adoption_mutates_engine_state": False,
        "requires_separate_engine_position_recovery": True,
        "symbol": str(status.get("symbol") or getattr(status, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
        "base_asset": runtime_awareness.get("base_asset"),
        "quote_asset": runtime_awareness.get("quote_asset"),
        "candidate_qty": qty,
        "candidate_mark_price": mark_price if mark_price > 0 else None,
        "candidate_notional": notional,
        "balance_review": balance_review,
        "reason_codes": reason_codes,
    }


def build_reconciliation_execution_snapshot(*, runtime_awareness: dict[str, Any], balance_review: dict[str, Any], risk_reconciliation: dict[str, Any], decision: dict[str, Any] | None, adoption_candidate: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether reconciliation has been cleared without weakening live/order gates."""

    decision = decision if isinstance(decision, dict) else {}
    decision_type = str(decision.get("decision_type") or "NONE")
    mismatch_active = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False))
    orphan_active = bool(runtime_awareness.get("orphan_local_position_recovery_detected", False))
    position_present = bool(runtime_awareness.get("position_present", False))
    tradable_base = _float_value(runtime_awareness.get("tradable_base"))
    base_dust = _float_value(runtime_awareness.get("base_dust"))
    dust_threshold = max(base_dust, 0.0)
    dust_safe_eligible = bool(mismatch_active and tradable_base <= dust_threshold and not position_present)

    reason_codes: list[str] = []
    if mismatch_active:
        reason_codes.append("BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED")
    if orphan_active:
        reason_codes.append("ORPHAN_RECOVERY_REQUIRES_RECONCILIATION")
    if decision_type == "BALANCE_SNAPSHOT_CONFIRMED":
        reason_codes.append("BALANCE_SNAPSHOT_CONFIRMED_READ_ONLY")
    if decision_type in {"DUST_SAFE_BASE_BALANCE_RESOLUTION", "DUST_SAFE_CLEAR_APPLIED"}:
        reason_codes.append("DUST_SAFE_RESOLUTION_RECORDED")
        if decision_type == "DUST_SAFE_CLEAR_APPLIED":
            reason_codes.append("DUST_SAFE_CLEAR_VALIDATION_APPLIED")
        if dust_safe_eligible:
            reason_codes.append("DUST_SAFE_BASE_BALANCE_ELIGIBLE")
        else:
            reason_codes.append("DUST_SAFE_BASE_BALANCE_NOT_ELIGIBLE")
    if decision_type in {"TRACKED_POSITION_ADOPTION_CANDIDATE", "TRACKED_POSITION_CANDIDATE_REVIEWED"}:
        reason_codes.append("TRACKED_POSITION_ADOPTION_CANDIDATE_RECORDED")
        if decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED":
            reason_codes.append("TRACKED_POSITION_CANDIDATE_REVIEW_APPLIED")
        reason_codes.append("ENGINE_POSITION_STATE_NOT_MUTATED")

    clear_by_no_mismatch = bool(not mismatch_active and not orphan_active)
    clear_by_dust_safe = bool(decision_type in {"DUST_SAFE_BASE_BALANCE_RESOLUTION", "DUST_SAFE_CLEAR_APPLIED"} and dust_safe_eligible)
    reconciliation_clear = bool(clear_by_no_mismatch or clear_by_dust_safe)
    if reconciliation_clear:
        reason_codes.append("RECONCILIATION_CLEAR")
    else:
        reason_codes.append("ENTRY_GUARD_RELEASE_BLOCKED_UNTIL_RECONCILIATION_CLEAR")

    return {
        "contract_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
        "enabled": True,
        "read_only_balance_snapshot_confirmation_enabled": True,
        "tracked_position_adoption_candidate_enabled": True,
        "dust_safe_base_balance_resolution_enabled": True,
        "manual_reconciliation_decision_ledger_enabled": True,
        "entry_guard_release_only_after_reconciliation_clear": True,
        "decision": decision,
        "decision_type": decision_type,
        "decision_present": bool(decision),
        "reconciliation_clear": reconciliation_clear,
        "entry_guard_release_authorized": reconciliation_clear,
        "clear_by_no_mismatch": clear_by_no_mismatch,
        "clear_by_dust_safe": clear_by_dust_safe,
        "dust_safe_threshold": dust_threshold,
        "dust_safe_eligible": dust_safe_eligible,
        "tracked_position_adoption_candidate": adoption_candidate,
        "balance_review": balance_review,
        "risk_reconciliation_status": risk_reconciliation.get("status"),
        "reason_codes": reason_codes,
    }


def build_reconciliation_decision_apply_snapshot(*, reconciliation_execution: dict[str, Any], decision: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize the manual reconciliation apply flow without mutating engine position state."""

    decision = decision if isinstance(decision, dict) else {}
    decision_type = str(decision.get("decision_type") or "NONE")
    release_authorized = bool(reconciliation_execution.get("entry_guard_release_authorized", False))
    reconciliation_clear = bool(reconciliation_execution.get("reconciliation_clear", False))
    reason_codes: list[str] = []
    if decision:
        reason_codes.append("MANUAL_RECONCILIATION_DECISION_PRESENT")
    else:
        reason_codes.append("MANUAL_RECONCILIATION_DECISION_NOT_PRESENT")
    if decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED":
        reason_codes.append("TRACKED_POSITION_CANDIDATE_REVIEW_RECORDED")
        reason_codes.append("ENGINE_POSITION_STATE_NOT_MUTATED")
        reason_codes.append("SEPARATE_ENGINE_POSITION_RECOVERY_REQUIRED")
    if decision_type == "DUST_SAFE_CLEAR_APPLIED":
        reason_codes.append("DUST_SAFE_CLEAR_DECISION_RECORDED")
        if reconciliation_clear:
            reason_codes.append("DUST_SAFE_CLEAR_VALIDATED")
        else:
            reason_codes.append("DUST_SAFE_CLEAR_REJECTED_NOT_ELIGIBLE")
    if release_authorized:
        reason_codes.append("ENTRY_GUARD_RELEASE_VERIFIED")
    else:
        reason_codes.append("ENTRY_GUARD_RELEASE_NOT_AUTHORIZED")

    if reconciliation_clear:
        apply_status = "RECONCILIATION_CLEAR"
    elif decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED":
        apply_status = "REVIEW_RECORDED_ENGINE_RECOVERY_REQUIRED"
    elif decision_type == "DUST_SAFE_CLEAR_APPLIED":
        apply_status = "REJECTED_NOT_DUST_SAFE"
    elif decision:
        apply_status = "DECISION_RECORDED_REVIEW_REQUIRED"
    else:
        apply_status = "WAITING_FOR_MANUAL_DECISION"

    return {
        "contract_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
        "enabled": True,
        "tracked_position_candidate_review_enabled": True,
        "dust_safe_clear_validation_enabled": True,
        "manual_reconciliation_decision_persistence_enabled": True,
        "entry_guard_release_verification_enabled": True,
        "runtime_lock_owner_mismatch_resolver_enabled": True,
        "decision": decision,
        "decision_type": decision_type,
        "decision_present": bool(decision),
        "apply_status": apply_status,
        "reconciliation_clear": reconciliation_clear,
        "entry_guard_release_verified": release_authorized,
        "engine_position_state_mutated": False,
        "requires_separate_engine_position_recovery": bool(decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED"),
        "reason_codes": reason_codes,
    }


def build_runtime_lock_owner_mismatch_resolver(runtime_lock: dict[str, Any], startup_error: str | None) -> dict[str, Any]:
    """Expose a safe resolver for dead/stale lock owner mismatch; never clears live owners automatically."""

    exists = bool(runtime_lock.get("exists", False))
    held_by_current = bool(runtime_lock.get("held_by_current_process", False))
    pid_alive = runtime_lock.get("pid_alive")
    owner_pid = runtime_lock.get("pid")
    owner_mismatch = bool(startup_error and exists and not held_by_current)
    owner_dead = bool(owner_mismatch and owner_pid is not None and pid_alive is False)
    owner_alive = bool(owner_mismatch and pid_alive is True)
    safe_clear_allowed = bool(owner_mismatch and runtime_lock.get("stale_reclaim_safe", False))
    reason_codes: list[str] = []
    if owner_mismatch:
        reason_codes.append("RUNTIME_LOCK_OWNER_MISMATCH")
    if owner_dead:
        reason_codes.append("LOCK_OWNER_PID_DEAD")
    if owner_alive:
        reason_codes.append("LOCK_OWNER_PID_ALIVE")
    if safe_clear_allowed:
        reason_codes.append("STALE_RUNTIME_LOCK_SAFE_CLEAR_AVAILABLE")
    elif owner_mismatch:
        reason_codes.append("RESTART_OR_MANUAL_OPERATOR_REVIEW_REQUIRED")
    if held_by_current:
        reason_codes.append("RUNTIME_LOCK_HELD_BY_CURRENT_PROCESS")
    return {
        "contract_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
        "enabled": True,
        "owner_mismatch_detected": owner_mismatch,
        "startup_error": startup_error,
        "lock_pid": owner_pid,
        "lock_pid_alive": pid_alive,
        "current_process_pid": os.getpid(),
        "held_by_current_process": held_by_current,
        "safe_clear_allowed": safe_clear_allowed,
        "resolve_confirmation": "CONFIRM_RESOLVE_RUNTIME_LOCK_OWNER_MISMATCH",
        "restart_required": bool(owner_mismatch and not safe_clear_allowed),
        "reason_codes": reason_codes,
    }



def build_engine_position_recovery_gate_snapshot(*, runtime_awareness: dict[str, Any], reconciliation_decision_apply: dict[str, Any], recovery_plan: dict[str, Any] | None) -> dict[str, Any]:
    """Expose the 33J fail-closed recovery plan apply and verification gate.

    The gate never mutates engine/runtime position state. It records a reviewed
    candidate, a manual external recovery plan, and a read-only verification.
    Entry guard release is verified only when the live snapshot has no active
    balance/position mismatch and no orphan recovery condition.
    """

    recovery_plan = recovery_plan if isinstance(recovery_plan, dict) else {}
    decision = _as_dict(reconciliation_decision_apply.get("decision"))
    candidate = _as_dict(decision.get("candidate"))
    decision_type = str(reconciliation_decision_apply.get("decision_type") or "NONE")
    reviewed_candidate = bool(decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED" and candidate.get("candidate_available", False))
    mismatch_active = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False))
    orphan_active = bool(runtime_awareness.get("orphan_local_position_recovery_detected", False))
    position_present = bool(runtime_awareness.get("position_present", False))
    plan_present = bool(recovery_plan)
    plan_confirmed = bool(recovery_plan.get("plan_confirmed", False))
    manual_external_recovery_confirmed = bool(recovery_plan.get("manual_external_recovery_confirmed", False))
    verification = _as_dict(recovery_plan.get("verification"))
    no_mismatch_verified_live = bool(not mismatch_active and not orphan_active)
    verification_recorded = bool(verification)
    verified_from_fresh_source = bool(verification.get("verified_from_fresh_exchange_source", False))
    verified_no_mismatch_recorded = bool(recovery_plan.get("verified_no_mismatch", False) and verification_recorded and verified_from_fresh_source)
    verified_no_mismatch = bool(plan_confirmed and manual_external_recovery_confirmed and (no_mismatch_verified_live or verified_no_mismatch_recorded))
    engine_position_verified = bool(verified_no_mismatch and position_present)
    empty_inventory_verified = bool(verified_no_mismatch and not position_present)
    entry_guard_release_verified = bool(verified_no_mismatch)
    reason_codes: list[str] = []
    if reviewed_candidate:
        reason_codes.append("REVIEWED_CANDIDATE_READY_FOR_RECOVERY_PLAN")
    else:
        reason_codes.append("REVIEWED_CANDIDATE_DECISION_REQUIRED")
    if plan_present:
        reason_codes.append("ENGINE_POSITION_RECOVERY_PLAN_PRESENT")
    else:
        reason_codes.append("ENGINE_POSITION_RECOVERY_PLAN_NOT_PRESENT")
    if plan_confirmed:
        reason_codes.append("ENGINE_POSITION_RECOVERY_PLAN_CONFIRMED")
    else:
        reason_codes.append("ENGINE_POSITION_RECOVERY_PLAN_NOT_CONFIRMED")
    if manual_external_recovery_confirmed:
        reason_codes.append("MANUAL_EXTERNAL_RECOVERY_PLAN_CONFIRMED")
    else:
        reason_codes.append("MANUAL_EXTERNAL_RECOVERY_PLAN_NOT_CONFIRMED")
    if mismatch_active:
        reason_codes.append("BALANCE_POSITION_MISMATCH_STILL_ACTIVE")
    else:
        reason_codes.append("BALANCE_POSITION_MISMATCH_CLEAR")
    if orphan_active:
        reason_codes.append("ORPHAN_RECOVERY_STILL_ACTIVE")
    else:
        reason_codes.append("ORPHAN_RECOVERY_CLEAR")
    if position_present:
        reason_codes.append("ENGINE_POSITION_PRESENT")
    else:
        reason_codes.append("ENGINE_POSITION_NOT_PRESENT")
    if verification_recorded:
        reason_codes.append("RECOVERY_COMPLETION_VERIFICATION_RECORDED")
    if verified_from_fresh_source:
        reason_codes.append("RECOVERY_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
    if engine_position_verified:
        reason_codes.append("ENGINE_POSITION_VERIFIED_AFTER_EXTERNAL_RECOVERY")
    if empty_inventory_verified:
        reason_codes.append("EMPTY_INVENTORY_VERIFIED_AFTER_EXTERNAL_RECOVERY")
    if entry_guard_release_verified:
        reason_codes.append("ENTRY_GUARD_RELEASE_VERIFIED_AFTER_NO_MISMATCH")
    else:
        reason_codes.append("ENTRY_GUARD_REMAINS_BLOCKED_UNTIL_VERIFIED_NO_MISMATCH")

    if entry_guard_release_verified:
        status = "RECOVERY_VERIFIED_NO_MISMATCH"
    elif plan_confirmed and manual_external_recovery_confirmed:
        status = "PLAN_CONFIRMED_WAITING_FOR_NO_MISMATCH_VERIFICATION"
    elif plan_present:
        status = "PLAN_CREATED_WAITING_FOR_MANUAL_EXTERNAL_RECOVERY_CONFIRMATION"
    elif reviewed_candidate:
        status = "WAITING_FOR_RECOVERY_PLAN"
    else:
        status = "WAITING_FOR_REVIEWED_CANDIDATE"

    recovery_plan_apply_verification_gate = {
        "contract_version": OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
        "enabled": True,
        "create_recovery_plan_from_reviewed_candidate_enabled": True,
        "confirm_manual_external_recovery_plan_enabled": True,
        "verify_engine_position_after_external_recovery_enabled": True,
        "recovery_completion_ledger_enabled": True,
        "entry_guard_release_only_after_verified_no_mismatch": True,
        "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "verified_from_fresh_exchange_source": verified_from_fresh_source,
        "verified_no_mismatch": verified_no_mismatch,
        "engine_position_verified": engine_position_verified,
        "empty_inventory_verified": empty_inventory_verified,
        "mismatch_active": mismatch_active,
        "orphan_recovery_detected": orphan_active,
        "position_present": position_present,
        "plan_confirmed": plan_confirmed,
        "manual_external_recovery_confirmed": manual_external_recovery_confirmed,
        "entry_guard_release_verified": entry_guard_release_verified,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "reason_codes": reason_codes,
    }

    return {
        "contract_version": OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION,
        "recovery_plan_apply_verification_gate_version": OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
        "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "enabled": True,
        "reviewed_candidate_to_recovery_plan_enabled": True,
        "manual_recovery_plan_confirmation_enabled": True,
        "no_auto_position_mutation": True,
        "recovery_ledger_enabled": True,
        "entry_guard_remains_blocked_until_engine_position_verified": True,
        "recovery_completion_verification_helper_enabled": True,
        "create_recovery_plan_from_reviewed_candidate_enabled": True,
        "confirm_manual_external_recovery_plan_enabled": True,
        "verify_engine_position_after_external_recovery_enabled": True,
        "recovery_completion_ledger_enabled": True,
        "entry_guard_release_only_after_verified_no_mismatch": True,
        "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "verified_from_fresh_exchange_source": verified_from_fresh_source,
        "decision_type": decision_type,
        "reviewed_candidate_present": reviewed_candidate,
        "candidate": candidate,
        "recovery_plan": recovery_plan,
        "plan_present": plan_present,
        "plan_confirmed": plan_confirmed,
        "manual_external_recovery_confirmed": manual_external_recovery_confirmed,
        "status": status,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "requires_manual_external_recovery": bool(reviewed_candidate and not entry_guard_release_verified),
        "external_recovery_verified": verified_no_mismatch,
        "verified_no_mismatch": verified_no_mismatch,
        "engine_position_verified": engine_position_verified,
        "empty_inventory_verified": empty_inventory_verified,
        "entry_guard_release_verified": entry_guard_release_verified,
        "position_present": position_present,
        "mismatch_active": mismatch_active,
        "orphan_recovery_detected": orphan_active,
        "verification": verification,
        "recovery_plan_apply_verification_gate": recovery_plan_apply_verification_gate,
        "reason_codes": reason_codes,
    }


def _safe_apply_verified_from_fresh_source(safe_apply: dict[str, Any]) -> bool:
    safe_apply = _as_dict(safe_apply)
    if not bool(safe_apply.get("verified_no_mismatch_with_evidence", False)):
        return False
    if bool(safe_apply.get("engine_position_state_mutated", False)) or bool(safe_apply.get("auto_position_mutation_performed", False)):
        return False
    if bool(safe_apply.get("verified_from_fresh_exchange_source", False)) or bool(safe_apply.get("verification_result_ok", False)):
        return True
    preflight = _as_dict(safe_apply.get("preflight"))
    source_gate = _as_dict(preflight.get("exchange_environment_source_gate"))
    return bool(
        preflight.get("preflight_passed", False)
        and preflight.get("no_mismatch_from_verified_fresh_source", False)
        and source_gate.get("no_mismatch_from_verified_fresh_source", False)
        and source_gate.get("fresh_exchange_balance_verified", False)
    )


def _safe_apply_source_gate(safe_apply: dict[str, Any], fallback_source_gate: dict[str, Any] | None = None) -> dict[str, Any]:
    safe_apply = _as_dict(safe_apply)
    preflight = _as_dict(safe_apply.get("preflight"))
    candidates = [
        _as_dict(preflight.get("exchange_environment_source_gate")),
        _as_dict(safe_apply.get("exchange_environment_source_gate")),
        _as_dict(fallback_source_gate),
    ]
    for candidate in candidates:
        if candidate.get("no_mismatch_from_verified_fresh_source") or candidate.get("fresh_exchange_balance_verified"):
            return candidate
    return candidates[-1]


def build_engine_status_balance_cache_reconciliation_snapshot(*, runtime_awareness: dict[str, Any], balance_review: dict[str, Any], evidence_state: dict[str, Any] | None, exchange_environment_source_gate: dict[str, Any] | None) -> dict[str, Any]:
    """33M: build a read-only runtime-cache reconciliation view from verified fresh source.

    This is deliberately not an engine mutation. It only prevents stale
    `engine_status_balances` from continuing to drive cockpit risk/entry state
    after 33K/33L safe apply has verified empty inventory from a fresh exchange
    source.
    """

    evidence_state = evidence_state if isinstance(evidence_state, dict) else {}
    safe_apply = _as_dict(evidence_state.get("verify_no_mismatch_safe_apply"))
    source_gate = _safe_apply_source_gate(safe_apply, exchange_environment_source_gate)
    fresh_base_free = _float_value(source_gate.get("fresh_base_free"))
    fresh_base_locked = _float_value(source_gate.get("fresh_base_locked"))
    fresh_base_tradable = _float_value(source_gate.get("fresh_base_tradable"))
    fresh_quote_free = _float_value(source_gate.get("fresh_quote_free"))
    verified_from_fresh = _safe_apply_verified_from_fresh_source(safe_apply)
    no_mismatch_from_fresh = bool(source_gate.get("no_mismatch_from_verified_fresh_source", False)) or bool(safe_apply.get("verified_from_fresh_exchange_source", False))
    engine_status_source_detected = str((balance_review.get("base") or {}).get("source") or source_gate.get("balance_review_source") or "").lower() == "engine_status_balances"
    stale_engine_mismatch_present = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False) or runtime_awareness.get("orphan_local_position_recovery_detected", False))
    active_anomaly_code = str(runtime_awareness.get("active_anomaly_code") or "").strip()
    unrelated_active_anomaly_present = bool(active_anomaly_code)
    empty_inventory_verified = bool(verified_from_fresh and no_mismatch_from_fresh and fresh_base_free <= 0 and fresh_base_locked <= 0 and fresh_base_tradable <= 0 and not bool(source_gate.get("runtime_position_present", False)))
    runtime_snapshot_override_active = bool(empty_inventory_verified and engine_status_source_detected and stale_engine_mismatch_present and not unrelated_active_anomaly_present)

    reason_codes: list[str] = []
    if engine_status_source_detected:
        reason_codes.append("ENGINE_STATUS_BALANCE_CACHE_DETECTED")
    if stale_engine_mismatch_present:
        reason_codes.append("STALE_ENGINE_BALANCE_MISMATCH_PRESENT")
    if verified_from_fresh:
        reason_codes.append("SAFE_APPLY_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
    else:
        reason_codes.append("SAFE_APPLY_FRESH_SOURCE_VERIFICATION_NOT_PRESENT")
    if no_mismatch_from_fresh:
        reason_codes.append("VERIFIED_FRESH_SOURCE_NO_MISMATCH")
    else:
        reason_codes.append("VERIFIED_FRESH_SOURCE_NO_MISMATCH_NOT_PRESENT")
    if empty_inventory_verified:
        reason_codes.append("EMPTY_INVENTORY_VERIFIED_FROM_FRESH_SOURCE")
    if unrelated_active_anomaly_present:
        reason_codes.append("ACTIVE_ANOMALY_PREVENTS_CACHE_OVERRIDE")
    if runtime_snapshot_override_active:
        reason_codes.append("RUNTIME_SNAPSHOT_OVERRIDE_ACTIVE")
        reason_codes.append("RISK_BADGE_RECOMPUTED_FROM_VERIFIED_FRESH_SOURCE")
        reason_codes.append("ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY")
    else:
        reason_codes.append("RUNTIME_SNAPSHOT_OVERRIDE_NOT_ACTIVE")

    return {
        "contract_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
        "enabled": True,
        "verified_fresh_source_to_runtime_snapshot_override_enabled": True,
        "stale_engine_balance_invalidated_enabled": True,
        "risk_badge_recompute_from_verified_fresh_source_enabled": True,
        "entry_guard_final_release_consistency_enabled": True,
        "runtime_snapshot_override_active": runtime_snapshot_override_active,
        "stale_engine_balance_invalidated": runtime_snapshot_override_active,
        "risk_badge_recomputed_from_verified_fresh_source": runtime_snapshot_override_active,
        "entry_guard_release_stabilized_after_safe_apply": bool(verified_from_fresh and no_mismatch_from_fresh),
        "verified_from_fresh_exchange_source": verified_from_fresh,
        "no_mismatch_from_verified_fresh_source": no_mismatch_from_fresh,
        "empty_inventory_verified": empty_inventory_verified,
        "engine_status_balance_source_detected": engine_status_source_detected,
        "stale_engine_mismatch_present": stale_engine_mismatch_present,
        "unrelated_active_anomaly_present": unrelated_active_anomaly_present,
        "fresh_base_free": fresh_base_free,
        "fresh_base_locked": fresh_base_locked,
        "fresh_base_tradable": fresh_base_tradable,
        "fresh_quote_free": fresh_quote_free,
        "source_gate": source_gate,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "reason_codes": reason_codes,
        "status": "RUNTIME_CACHE_RECONCILED_FROM_VERIFIED_FRESH_SOURCE" if runtime_snapshot_override_active else "WAITING_FOR_VERIFIED_FRESH_SOURCE_CACHE_RECONCILIATION",
    }


def apply_engine_status_balance_cache_reconciliation(runtime_awareness: dict[str, Any], balance_review: dict[str, Any], reconciliation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not bool(reconciliation.get("runtime_snapshot_override_active", False)):
        return runtime_awareness, balance_review
    updated_awareness = dict(runtime_awareness)
    suppressed_reason_codes = list(updated_awareness.get("reason_codes") or [])
    base_asset = str(updated_awareness.get("base_asset") or (balance_review.get("base_asset") if isinstance(balance_review, dict) else "UNKNOWN") or "UNKNOWN")
    quote_asset = str(updated_awareness.get("quote_asset") or (balance_review.get("quote_asset") if isinstance(balance_review, dict) else "UNKNOWN") or "UNKNOWN")
    updated_awareness.update({
        "contract_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
        "risk_badge": "GREEN",
        "banner_title": "Runtime inventory reconciled from verified fresh exchange source",
        "banner_message": "33M invalidated stale engine_status_balances for cockpit risk state after 33K/33L safe apply verified empty inventory from a fresh exchange source.",
        "recommended_action": "NONE",
        "reason_codes": ["ENGINE_STATUS_BALANCE_CACHE_RECONCILED_FROM_VERIFIED_FRESH_SOURCE"],
        "suppressed_stale_engine_reason_codes": suppressed_reason_codes,
        "base_free": _float_value(reconciliation.get("fresh_base_free")),
        "base_locked": _float_value(reconciliation.get("fresh_base_locked")),
        "base_dust": 0.0,
        "tradable_base": _float_value(reconciliation.get("fresh_base_tradable")),
        "base_balance_present": False,
        "position_present": False,
        "base_balance_present_position_not_tracked": False,
        "orphan_local_position_recovery_detected": False,
        "active_anomaly_code": None,
        "auto_entry_risk_attention_required": False,
        "engine_status_balance_cache_reconciliation": reconciliation,
    })
    updated_review = dict(balance_review)
    updated_review.update({
        "contract_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
        "read_only": True,
        "review_required": False,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "base": {
            "free": _float_value(reconciliation.get("fresh_base_free")),
            "locked": _float_value(reconciliation.get("fresh_base_locked")),
            "dust": 0.0,
            "tradable": _float_value(reconciliation.get("fresh_base_tradable")),
            "source": "verified_fresh_exchange_balance_33M",
        },
        "quote": {
            "free": _float_value(reconciliation.get("fresh_quote_free")),
            "locked": 0.0,
            "source": "verified_fresh_exchange_balance_33M",
        },
        "position_present": False,
        "pending_present": bool(balance_review.get("pending_present", False)),
        "base_balance_present_position_not_tracked": False,
        "engine_status_balance_cache_reconciliation": reconciliation,
        "reason_codes": ["ENGINE_STATUS_BALANCE_CACHE_RECONCILED_FROM_VERIFIED_FRESH_SOURCE"],
    })
    return updated_awareness, updated_review


def apply_engine_status_balance_cache_reconciliation_to_source_gate(source_gate: dict[str, Any], reconciliation: dict[str, Any]) -> dict[str, Any]:
    if not bool(reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False)):
        return source_gate
    updated = dict(source_gate)
    reason_codes = list(updated.get("reason_codes") or [])
    for code in (
        "SAFE_APPLY_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE",
        "ENGINE_STATUS_BALANCE_CACHE_RECONCILED_FROM_VERIFIED_FRESH_SOURCE",
        "ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY",
    ):
        if code not in reason_codes:
            reason_codes.append(code)
    updated.update({
        "contract_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "engine_status_balance_cache_reconciliation_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
        "engine_status_balance_cache_reconciliation": reconciliation,
        "engine_status_balance_source_rejected": True,
        "no_mismatch_from_verified_fresh_source": True,
        "entry_guard_release_verified": True,
        "fresh_base_free": _float_value(reconciliation.get("fresh_base_free")),
        "fresh_base_locked": _float_value(reconciliation.get("fresh_base_locked")),
        "fresh_base_tradable": _float_value(reconciliation.get("fresh_base_tradable")),
        "fresh_quote_free": _float_value(reconciliation.get("fresh_quote_free")),
        "fresh_mismatch_active": False,
        "runtime_position_present": False,
        "reason_codes": reason_codes,
        "status": "FRESH_SOURCE_SAFE_APPLY_STABILIZED_RUNTIME_CACHE_RECONCILED",
    })
    return updated


def build_external_recovery_evidence_gate_snapshot(*, runtime_awareness: dict[str, Any], engine_position_recovery_gate: dict[str, Any], evidence_state: dict[str, Any] | None, exchange_environment_source_gate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose 33K evidence + fresh snapshot gate for manual external recovery.

    This gate is deliberately fail-closed. Evidence capture, post-recovery
    snapshots and preflight records never mutate runtime position state. The
    entry guard can only be released when evidence exists, a fresh read-only
    post-recovery snapshot exists, and the no-mismatch preflight has passed.
    """

    evidence_state = evidence_state if isinstance(evidence_state, dict) else {}
    evidence = _as_dict(evidence_state.get("latest_evidence"))
    post_snapshot = _as_dict(evidence_state.get("post_recovery_snapshot"))
    preflight = _as_dict(evidence_state.get("no_mismatch_preflight"))
    safe_apply = _as_dict(evidence_state.get("verify_no_mismatch_safe_apply"))
    now = utc_ms()
    snapshot_captured_at_ms = int(post_snapshot.get("captured_at_ms") or 0)
    snapshot_age_ms = max(now - snapshot_captured_at_ms, 0) if snapshot_captured_at_ms else None
    fresh_snapshot = bool(snapshot_captured_at_ms and snapshot_age_ms is not None and snapshot_age_ms <= 120_000)
    live_mismatch_active = bool(runtime_awareness.get("base_balance_present_position_not_tracked", False))
    live_orphan_active = bool(runtime_awareness.get("orphan_local_position_recovery_detected", False))
    post_mismatch_active = bool(post_snapshot.get("mismatch_active", live_mismatch_active)) if post_snapshot else live_mismatch_active
    post_orphan_active = bool(post_snapshot.get("orphan_recovery_detected", live_orphan_active)) if post_snapshot else live_orphan_active
    source_gate = exchange_environment_source_gate if isinstance(exchange_environment_source_gate, dict) else {}
    source_gate_enabled = bool(source_gate)
    fresh_source_verified = bool(source_gate.get("fresh_exchange_balance_verified", False))
    no_mismatch_from_fresh_source = bool(source_gate.get("no_mismatch_from_verified_fresh_source", False))
    engine_status_source_rejected = bool(source_gate.get("engine_status_balance_source_rejected", False))
    no_mismatch_preflight_passed = bool(preflight.get("preflight_passed", False))
    verified_no_mismatch_with_evidence = bool(safe_apply.get("verified_no_mismatch_with_evidence", False))
    safe_apply_verified_from_fresh_source = _safe_apply_verified_from_fresh_source(safe_apply)
    plan_present = bool(engine_position_recovery_gate.get("plan_present", False))
    plan_confirmed = bool(engine_position_recovery_gate.get("plan_confirmed", False))
    manual_external_confirmed = bool(engine_position_recovery_gate.get("manual_external_recovery_confirmed", False))
    evidence_present = bool(evidence)
    post_snapshot_present = bool(post_snapshot)
    evidence_complete = bool(evidence_present and evidence.get("recovery_mode") and evidence.get("operator_attestation"))
    stable_fresh_source_release = bool(safe_apply_verified_from_fresh_source and verified_no_mismatch_with_evidence)
    entry_guard_release_verified = bool(verified_no_mismatch_with_evidence and no_mismatch_preflight_passed and evidence_complete and (fresh_snapshot or stable_fresh_source_release) and (not source_gate_enabled or no_mismatch_from_fresh_source or stable_fresh_source_release))

    reason_codes: list[str] = []
    if evidence_present:
        reason_codes.append("EXTERNAL_RECOVERY_EVIDENCE_PRESENT")
    else:
        reason_codes.append("EXTERNAL_RECOVERY_EVIDENCE_NOT_PRESENT")
    if evidence_complete:
        reason_codes.append("EXTERNAL_RECOVERY_EVIDENCE_COMPLETE")
    else:
        reason_codes.append("EXTERNAL_RECOVERY_EVIDENCE_INCOMPLETE")
    if post_snapshot_present:
        reason_codes.append("POST_RECOVERY_READ_ONLY_SNAPSHOT_PRESENT")
    else:
        reason_codes.append("POST_RECOVERY_READ_ONLY_SNAPSHOT_NOT_PRESENT")
    if fresh_snapshot:
        reason_codes.append("POST_RECOVERY_SNAPSHOT_FRESH")
    else:
        reason_codes.append("POST_RECOVERY_SNAPSHOT_NOT_FRESH")
    if source_gate_enabled and (no_mismatch_from_fresh_source or stable_fresh_source_release):
        reason_codes.append("NO_MISMATCH_PREFLIGHT_FRESH_SOURCE_MISMATCH_CLEAR")
    elif post_mismatch_active or live_mismatch_active:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_BLOCKED_MISMATCH_ACTIVE")
    else:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_MISMATCH_CLEAR")
    if source_gate_enabled and (no_mismatch_from_fresh_source or stable_fresh_source_release):
        reason_codes.append("NO_MISMATCH_PREFLIGHT_FRESH_SOURCE_ORPHAN_CLEAR")
    elif post_orphan_active or live_orphan_active:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_BLOCKED_ORPHAN_ACTIVE")
    else:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_ORPHAN_CLEAR")
    if source_gate_enabled and engine_status_source_rejected:
        reason_codes.append("ENGINE_STATUS_BALANCE_SOURCE_REJECTED_FOR_NO_MISMATCH")
    if source_gate_enabled and (fresh_source_verified or stable_fresh_source_release):
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_VERIFIED")
    elif source_gate_enabled:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_NOT_VERIFIED")
    if stable_fresh_source_release:
        reason_codes.append("SAFE_APPLY_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
        reason_codes.append("ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY")
    if plan_confirmed and manual_external_confirmed:
        reason_codes.append("MANUAL_EXTERNAL_RECOVERY_PLAN_CONFIRMED")
    else:
        reason_codes.append("MANUAL_EXTERNAL_RECOVERY_PLAN_NOT_CONFIRMED")
    if no_mismatch_preflight_passed:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_PASSED")
    else:
        reason_codes.append("NO_MISMATCH_PREFLIGHT_NOT_PASSED")
    if verified_no_mismatch_with_evidence:
        reason_codes.append("VERIFY_NO_MISMATCH_SAFE_APPLY_RECORDED")
    else:
        reason_codes.append("VERIFY_NO_MISMATCH_SAFE_APPLY_NOT_RECORDED")
    if entry_guard_release_verified:
        reason_codes.append("ENTRY_GUARD_RELEASE_VERIFIED_WITH_EVIDENCE_AND_FRESH_SNAPSHOT")
    else:
        reason_codes.append("ENTRY_GUARD_REMAINS_BLOCKED_UNTIL_EVIDENCE_AND_FRESH_NO_MISMATCH")

    if entry_guard_release_verified:
        status = "EVIDENCE_VERIFIED_NO_MISMATCH"
    elif no_mismatch_preflight_passed:
        status = "NO_MISMATCH_PREFLIGHT_PASSED_WAITING_FOR_SAFE_APPLY"
    elif evidence_present and post_snapshot_present:
        status = "EVIDENCE_CAPTURED_WAITING_FOR_NO_MISMATCH_PREFLIGHT"
    elif evidence_present:
        status = "EVIDENCE_CAPTURED_WAITING_FOR_POST_RECOVERY_SNAPSHOT"
    elif plan_present and plan_confirmed and manual_external_confirmed:
        status = "WAITING_FOR_EXTERNAL_RECOVERY_EVIDENCE"
    else:
        status = "WAITING_FOR_CONFIRMED_RECOVERY_PLAN"

    return {
        "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
        "enabled": True,
        "manual_recovery_evidence_capture_enabled": True,
        "read_only_post_recovery_balance_snapshot_enabled": True,
        "no_mismatch_preflight_enabled": True,
        "verify_no_mismatch_safe_apply_enabled": True,
        "entry_guard_release_only_with_evidence_and_fresh_snapshot": True,
        "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "fresh_exchange_balance_required": True,
        "fresh_exchange_balance_verified": bool(fresh_source_verified or stable_fresh_source_release),
        "safe_apply_verified_from_fresh_source": stable_fresh_source_release,
        "no_mismatch_from_verified_fresh_source": bool(no_mismatch_from_fresh_source or stable_fresh_source_release),
        "engine_status_balance_source_rejected": engine_status_source_rejected,
        "no_auto_position_mutation": True,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "plan_present": plan_present,
        "plan_confirmed": plan_confirmed,
        "manual_external_recovery_confirmed": manual_external_confirmed,
        "evidence_present": evidence_present,
        "evidence_complete": evidence_complete,
        "post_recovery_snapshot_present": post_snapshot_present,
        "post_recovery_snapshot_fresh": fresh_snapshot,
        "post_recovery_snapshot_age_ms": snapshot_age_ms,
        "no_mismatch_preflight_passed": no_mismatch_preflight_passed,
        "verified_no_mismatch_with_evidence": verified_no_mismatch_with_evidence,
        "entry_guard_release_verified": entry_guard_release_verified,
        "mismatch_active": bool(live_mismatch_active or post_mismatch_active),
        "orphan_recovery_detected": bool(live_orphan_active or post_orphan_active),
        "mismatch_active_from_verified_fresh_source": False if (no_mismatch_from_fresh_source or stable_fresh_source_release) else None,
        "exchange_environment_source_gate": source_gate,
        "evidence": evidence,
        "post_recovery_snapshot": post_snapshot,
        "no_mismatch_preflight": preflight,
        "verify_no_mismatch_safe_apply": safe_apply,
        "status": status,
        "reason_codes": reason_codes,
    }


def _safe_setting_text(settings: Any, *names: str) -> str:
    for name in names:
        value = getattr(settings, name, None)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _safe_url_host(value: str) -> str:
    try:
        return str(urlparse(str(value or "")).netloc or value or "").strip().lower()
    except Exception:
        return str(value or "").strip().lower()


def _symbol_assets_from_settings(settings: Any, runtime_awareness: dict[str, Any]) -> tuple[str, str, str]:
    symbol = str(_safe_setting_text(settings, "symbol", "trading_symbol", "default_symbol") or runtime_awareness.get("symbol") or "UNKNOWN").upper()
    base_asset = str(runtime_awareness.get("base_asset") or "UNKNOWN").upper()
    quote_asset = str(runtime_awareness.get("quote_asset") or "UNKNOWN").upper()
    if base_asset == "UNKNOWN" or quote_asset == "UNKNOWN":
        inferred_base, inferred_quote = _infer_assets(symbol, {})
        base_asset = base_asset if base_asset != "UNKNOWN" else inferred_base
        quote_asset = quote_asset if quote_asset != "UNKNOWN" else inferred_quote
    return symbol, base_asset, quote_asset


def build_exchange_environment_config_audit(settings: Any, *, runtime_awareness: dict[str, Any]) -> dict[str, Any]:
    symbol, base_asset, quote_asset = _symbol_assets_from_settings(settings, runtime_awareness)
    market_type = _safe_setting_text(settings, "market_type")
    execution_mode = _safe_setting_text(settings, "execution_mode")
    base_url = _safe_setting_text(settings, "base_url", "api_url", "binance_base_url")
    host = _safe_url_host(base_url)
    demo_spot_market = market_type.lower() == "spot_demo"
    demo_execution = execution_mode.lower() == "live_demo"
    demo_base_url = host == "demo-api.binance.com"
    symbol_ok = bool(symbol and symbol != "UNKNOWN" and base_asset != "UNKNOWN" and quote_asset != "UNKNOWN")
    consistent = bool(demo_spot_market and demo_execution and demo_base_url and symbol_ok)
    reason_codes: list[str] = []
    reason_codes.append("CONFIG_MARKET_TYPE_SPOT_DEMO" if demo_spot_market else "CONFIG_MARKET_TYPE_NOT_SPOT_DEMO")
    reason_codes.append("CONFIG_EXECUTION_MODE_LIVE_DEMO" if demo_execution else "CONFIG_EXECUTION_MODE_NOT_LIVE_DEMO")
    reason_codes.append("CONFIG_BASE_URL_DEMO_API_BINANCE" if demo_base_url else "CONFIG_BASE_URL_NOT_DEMO_API_BINANCE")
    reason_codes.append("CONFIG_SYMBOL_ASSETS_RESOLVED" if symbol_ok else "CONFIG_SYMBOL_ASSETS_NOT_RESOLVED")
    reason_codes.append("EXCHANGE_ENVIRONMENT_CONFIG_CONSISTENT" if consistent else "EXCHANGE_ENVIRONMENT_CONFIG_INCONSISTENT")
    return {
        "contract_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "market_type": market_type,
        "execution_mode": execution_mode,
        "base_url_host": host,
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "demo_spot_market": demo_spot_market,
        "demo_execution_mode": demo_execution,
        "demo_base_url": demo_base_url,
        "config_environment_consistent": consistent,
        "reason_codes": reason_codes,
    }


def _extract_asset_balance(raw: Any, asset: str) -> dict[str, float]:
    asset = str(asset or "").upper()
    result = {"free": 0.0, "locked": 0.0, "total": 0.0}
    if not asset:
        return result
    if isinstance(raw, list):
        for item in raw:
            data = _as_dict(item)
            if str(data.get("asset") or data.get("currency") or data.get("coin") or "").upper() == asset:
                free = _float_value(data.get("free", data.get("available", data.get("balance"))))
                locked = _float_value(data.get("locked", data.get("used", data.get("hold"))))
                total = _float_value(data.get("total"), free + locked)
                return {"free": free, "locked": locked, "total": total}
        return result
    payload = _as_dict(raw)
    if "balances" in payload:
        return _extract_asset_balance(payload.get("balances"), asset)
    if asset in payload:
        data = payload.get(asset)
        if isinstance(data, dict):
            free = _float_value(data.get("free", data.get("available", data.get("balance"))))
            locked = _float_value(data.get("locked", data.get("used", data.get("hold"))))
            total = _float_value(data.get("total"), free + locked)
            return {"free": free, "locked": locked, "total": total}
        value = _float_value(data)
        return {"free": value, "locked": 0.0, "total": value}
    free_map = _as_dict(payload.get("free"))
    used_map = _as_dict(payload.get("used"))
    total_map = _as_dict(payload.get("total"))
    if asset in free_map or asset in used_map or asset in total_map:
        free = _float_value(free_map.get(asset))
        locked = _float_value(used_map.get(asset))
        total = _float_value(total_map.get(asset), free + locked)
        return {"free": free, "locked": locked, "total": total}
    for key in ("assets", "positions"):
        if isinstance(payload.get(key), list):
            found = _extract_asset_balance(payload.get(key), asset)
            if found.get("free") or found.get("locked") or found.get("total"):
                return found
    return result


def _normalize_fresh_exchange_balance(raw: Any, *, base_asset: str, quote_asset: str, dust_floor: float) -> dict[str, Any]:
    base = _extract_asset_balance(raw, base_asset)
    quote = _extract_asset_balance(raw, quote_asset)
    base_free = _float_value(base.get("free"))
    base_locked = _float_value(base.get("locked"))
    quote_free = _float_value(quote.get("free"))
    quote_locked = _float_value(quote.get("locked"))
    dust = max(_float_value(dust_floor), 0.0)
    tradable_base = max(base_free - dust, 0.0) if dust > 0 else max(base_free, 0.0)
    return {
        "base": {
            "asset": base_asset,
            "free": base_free,
            "locked": base_locked,
            "total": _float_value(base.get("total"), base_free + base_locked),
            "dust": min(base_free, dust) if dust > 0 else 0.0,
            "tradable": tradable_base,
            "source": "fresh_exchange_balance",
        },
        "quote": {
            "asset": quote_asset,
            "free": quote_free,
            "locked": quote_locked,
            "total": _float_value(quote.get("total"), quote_free + quote_locked),
            "source": "fresh_exchange_balance",
        },
    }


def _object_candidates(engine: Any) -> list[Any]:
    candidates = [engine]
    for name in (
        "exchange", "client", "binance", "binance_client", "exchange_client",
        "spot_client", "futures_client", "api_client", "rest_client", "connector",
    ):
        try:
            obj = getattr(engine, name, None)
        except Exception:
            obj = None
        if obj is not None and obj not in candidates:
            candidates.append(obj)
    return candidates


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _callable_without_required_args(method: Any) -> bool:
    try:
        sig = inspect.signature(method)
    except Exception:
        return True
    for param in sig.parameters.values():
        if param.default is inspect._empty and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            return False
    return True


async def fetch_fresh_exchange_balance_source(engine: Any, settings: Any, *, base_asset: str, quote_asset: str, dust_floor: float) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    method_names = (
        "fetch_balance", "fetch_balances", "get_balances", "get_account_balances",
        "fetch_account_balances", "get_account", "account", "get_account_info",
        "get_spot_account", "spot_account", "account_info", "fetch_account",
    )
    for obj in _object_candidates(engine):
        obj_name = obj.__class__.__name__
        for method_name in method_names:
            method = getattr(obj, method_name, None)
            if not callable(method):
                continue
            if not _callable_without_required_args(method):
                attempts.append({"object": obj_name, "method": method_name, "called": False, "reason": "required_arguments_present"})
                continue
            try:
                raw = await _maybe_await(method())
                normalized = _normalize_fresh_exchange_balance(raw, base_asset=base_asset, quote_asset=quote_asset, dust_floor=dust_floor)
                attempts.append({"object": obj_name, "method": method_name, "called": True, "ok": True})
                return {
                    "ok": True,
                    "source_object": obj_name,
                    "source_method": method_name,
                    "balances": normalized,
                    "attempts": attempts[-8:],
                }
            except Exception as exc:
                attempts.append({"object": obj_name, "method": method_name, "called": True, "ok": False, "error": str(exc)[:300]})
    return {
        "ok": False,
        "source_object": None,
        "source_method": None,
        "balances": {},
        "attempts": attempts[-20:],
        "error": "No zero-argument fresh balance method succeeded on engine/client objects.",
    }


def build_exchange_environment_source_gate_snapshot(*, settings: Any, runtime_awareness: dict[str, Any], balance_review: dict[str, Any], source_state: dict[str, Any] | None) -> dict[str, Any]:
    source_state = source_state if isinstance(source_state, dict) else {}
    config_audit = build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)
    latest = _as_dict(source_state.get("fresh_balance_source"))
    now = utc_ms()
    captured_at_ms = int(latest.get("captured_at_ms") or 0)
    age_ms = max(now - captured_at_ms, 0) if captured_at_ms else None
    fresh = bool(captured_at_ms and age_ms is not None and age_ms <= 60_000)
    balance_source = str(_as_dict(balance_review.get("base")).get("source") or "UNKNOWN")
    fresh_ok = bool(latest.get("ok", False))
    fresh_verified = bool(fresh_ok and fresh and config_audit.get("config_environment_consistent", False))
    latest_balances = _as_dict(latest.get("balances"))
    latest_base = _as_dict(latest_balances.get("base"))
    latest_quote = _as_dict(latest_balances.get("quote"))
    base_tradable = _float_value(latest_base.get("tradable"))
    base_free = _float_value(latest_base.get("free"))
    base_locked = _float_value(latest_base.get("locked"))
    position_present = bool(runtime_awareness.get("position_present", False))
    fresh_mismatch_active = bool(fresh_verified and (base_tradable > 0 or base_locked > 0) and not position_present)
    no_mismatch_from_verified_fresh_source = bool(fresh_verified and not fresh_mismatch_active)
    engine_status_balance_source_rejected = bool(balance_source == "engine_status_balances" and not no_mismatch_from_verified_fresh_source)
    reason_codes: list[str] = [*list(config_audit.get("reason_codes", []))]
    if latest:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_PRESENT")
    else:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_NOT_PRESENT")
    if fresh:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_FRESH")
    else:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_NOT_FRESH")
    if fresh_verified:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_VERIFIED")
    else:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_SOURCE_NOT_VERIFIED")
    if balance_source == "engine_status_balances":
        reason_codes.append("ENGINE_STATUS_BALANCE_SOURCE_DETECTED")
    if engine_status_balance_source_rejected:
        reason_codes.append("STALE_ENGINE_BALANCE_SNAPSHOT_REJECTED")
    if fresh_mismatch_active:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_MISMATCH_ACTIVE")
    elif fresh_verified:
        reason_codes.append("FRESH_EXCHANGE_BALANCE_NO_MISMATCH")
    if no_mismatch_from_verified_fresh_source:
        reason_codes.append("NO_MISMATCH_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
    else:
        reason_codes.append("NO_MISMATCH_NOT_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
    return {
        "contract_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "enabled": True,
        "config_environment_audit_enabled": True,
        "demo_spot_vs_engine_balance_source_verification_enabled": True,
        "fresh_exchange_balance_read_required": True,
        "stale_engine_balance_snapshot_rejection_enabled": True,
        "no_mismatch_verification_only_from_verified_fresh_source": True,
        "config_audit": config_audit,
        "balance_review_source": balance_source,
        "engine_status_balance_source_rejected": engine_status_balance_source_rejected,
        "fresh_exchange_balance_present": bool(latest),
        "fresh_exchange_balance_fresh": fresh,
        "fresh_exchange_balance_age_ms": age_ms,
        "fresh_exchange_balance_verified": fresh_verified,
        "fresh_exchange_balance": latest,
        "base_asset": latest_base.get("asset") or config_audit.get("base_asset"),
        "quote_asset": latest_quote.get("asset") or config_audit.get("quote_asset"),
        "fresh_base_free": base_free,
        "fresh_base_locked": base_locked,
        "fresh_base_tradable": base_tradable,
        "fresh_quote_free": _float_value(latest_quote.get("free")),
        "fresh_mismatch_active": fresh_mismatch_active,
        "runtime_position_present": position_present,
        "no_mismatch_from_verified_fresh_source": no_mismatch_from_verified_fresh_source,
        "entry_guard_release_verified": no_mismatch_from_verified_fresh_source,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "reason_codes": reason_codes,
        "status": "FRESH_SOURCE_VERIFIED_NO_MISMATCH" if no_mismatch_from_verified_fresh_source else "WAITING_FOR_VERIFIED_FRESH_EXCHANGE_BALANCE_SOURCE",
    }



# --- 4B.4.3.6.6.34 demo entry execution controlled re-enablement helpers ---
def _demo_entry_execution_key(settings: Any) -> str:
    """Return the symbol-scoped persistence key for 34 demo entry execution gate."""
    symbol = getattr(settings, "symbol", None) or getattr(settings, "trading_symbol", None) or getattr(settings, "default_symbol", None)
    symbol_text = str(symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    return f"operator_cockpit:demo_entry_execution:{symbol_text}"


def _latest_dict(items: Any) -> dict[str, Any]:
    if isinstance(items, list) and items:
        value = items[-1]
        return value if isinstance(value, dict) else {}
    return {}


def _truthy_text(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def _settings_text(settings: Any, *names: str, default: str = "") -> str:
    for name in names:
        value = getattr(settings, name, None)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _settings_float(settings: Any, *names: str, default: float | None = None) -> float | None:
    for name in names:
        value = getattr(settings, name, None)
        try:
            if value is not None and str(value).strip() != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _is_demo_spot_runtime(settings: Any) -> bool:
    market_type = _settings_text(settings, "market_type", "trading_mode", default="").lower()
    execution_mode = _settings_text(settings, "execution_mode", "mode", default="").lower()
    base_url = _settings_text(settings, "base_url", "api_base_url", "binance_base_url", default="").lower()
    return bool(market_type == "spot_demo" and execution_mode == "live_demo" and "demo-api.binance.com" in base_url)


def _extract_mark_price(status: dict[str, Any], spec: dict[str, Any] | None = None) -> float | None:
    spec = spec if isinstance(spec, dict) else {}
    candidates: list[Any] = [
        spec.get("mark_price"),
        spec.get("price"),
        spec.get("last_price"),
        spec.get("current_price"),
        status.get("mark_price"),
        status.get("price"),
        status.get("last_price"),
        status.get("current_price"),
    ]
    position = _as_dict(status.get("position_snapshot"))
    candidates.extend([position.get("mark_price"), position.get("entry_price")])
    ticker = _as_dict(status.get("ticker"))
    candidates.extend([ticker.get("lastPrice"), ticker.get("last_price"), ticker.get("price")])
    market = _as_dict(status.get("market"))
    candidates.extend([market.get("mark_price"), market.get("last_price"), market.get("price")])
    for candidate in candidates:
        value = _float_value(candidate, 0.0)
        if value > 0:
            return value
    return None


def _extract_symbol_filters(status: dict[str, Any], settings: Any) -> dict[str, Any]:
    """Extract entry filters from status/settings without exchange mutation.

    The helper is deliberately tolerant because Binance filter payloads can be
    represented as dicts, lists, or pre-normalized engine snapshots.
    """
    candidates: list[Any] = [
        status.get("symbol_filters"),
        status.get("exchange_filters"),
        status.get("filters"),
        _as_dict(status.get("symbol_info")).get("filters"),
        _as_dict(status.get("exchange_info")).get("filters"),
    ]
    normalized: dict[str, Any] = {}
    for raw in candidates:
        if isinstance(raw, dict):
            normalized.update(raw)
        elif isinstance(raw, list):
            for item in raw:
                item_dict = _as_dict(item)
                filter_type = str(item_dict.get("filterType") or item_dict.get("filter_type") or "").upper()
                if filter_type in {"LOT_SIZE", "MARKET_LOT_SIZE"}:
                    normalized.setdefault("min_qty", item_dict.get("minQty") or item_dict.get("min_qty"))
                    normalized.setdefault("max_qty", item_dict.get("maxQty") or item_dict.get("max_qty"))
                    normalized.setdefault("step_size", item_dict.get("stepSize") or item_dict.get("step_size"))
                elif filter_type in {"MIN_NOTIONAL", "NOTIONAL"}:
                    normalized.setdefault("min_notional", item_dict.get("minNotional") or item_dict.get("min_notional") or item_dict.get("notional"))
    return {
        "min_notional": _float_value(normalized.get("min_notional"), _settings_float(settings, "min_notional", "min_order_notional", default=5.0) or 5.0),
        "min_qty": _float_value(normalized.get("min_qty"), _settings_float(settings, "min_qty", "quantity_min", default=0.0001) or 0.0001),
        "max_qty": _float_value(normalized.get("max_qty"), _settings_float(settings, "max_qty", "quantity_max", default=0.0) or 0.0),
        "step_size": _float_value(normalized.get("step_size"), _settings_float(settings, "step_size", "quantity_step", default=0.0001) or 0.0001),
        "source": "status_or_settings",
    }


def _floor_to_step(value: float, step: float) -> float:
    if step <= 0:
        return max(value, 0.0)
    return max((int(value / step)) * step, 0.0)


def _build_demo_entry_filter_review(status: dict[str, Any], settings: Any, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec if isinstance(spec, dict) else {}
    symbol = str(spec.get("symbol") or getattr(settings, "symbol", "UNKNOWN") or "UNKNOWN").upper()
    side = str(spec.get("side") or "BUY").upper()
    mark_price = _extract_mark_price(status, spec)
    filters = _extract_symbol_filters(status, settings)
    quote_amount = _float_value(spec.get("quote_amount"), _settings_float(settings, "demo_entry_quote_amount", "default_order_quote_amount", "order_quote_amount", default=10.0) or 10.0)
    explicit_qty = _float_value(spec.get("quantity"), 0.0)
    raw_qty = explicit_qty if explicit_qty > 0 else (quote_amount / mark_price if mark_price and mark_price > 0 else 0.0)
    step_size = _float_value(filters.get("step_size"), 0.0)
    qty = _floor_to_step(raw_qty, step_size)
    notional = qty * mark_price if mark_price else 0.0
    min_notional = _float_value(filters.get("min_notional"), 0.0)
    min_qty = _float_value(filters.get("min_qty"), 0.0)
    max_qty = _float_value(filters.get("max_qty"), 0.0)
    reason_codes: list[str] = []
    if side != "BUY":
        reason_codes.append("DEMO_ENTRY_ONLY_BUY_SUPPORTED")
    if mark_price and mark_price > 0:
        reason_codes.append("ENTRY_MARK_PRICE_AVAILABLE")
    else:
        reason_codes.append("ENTRY_MARK_PRICE_MISSING")
    if qty > 0:
        reason_codes.append("ENTRY_QUANTITY_COMPUTED")
    else:
        reason_codes.append("ENTRY_QUANTITY_NOT_COMPUTED")
    if min_qty <= 0 or qty >= min_qty:
        reason_codes.append("ENTRY_MIN_QTY_SATISFIED")
    else:
        reason_codes.append("ENTRY_MIN_QTY_NOT_SATISFIED")
    if max_qty <= 0 or qty <= max_qty:
        reason_codes.append("ENTRY_MAX_QTY_SATISFIED")
    else:
        reason_codes.append("ENTRY_MAX_QTY_NOT_SATISFIED")
    if min_notional <= 0 or notional >= min_notional:
        reason_codes.append("ENTRY_MIN_NOTIONAL_SATISFIED")
    else:
        reason_codes.append("ENTRY_MIN_NOTIONAL_NOT_SATISFIED")
    filters_ok = bool(side == "BUY" and mark_price and mark_price > 0 and qty > 0 and (min_qty <= 0 or qty >= min_qty) and (max_qty <= 0 or qty <= max_qty) and (min_notional <= 0 or notional >= min_notional))
    return {
        "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
        "symbol": symbol,
        "side": side,
        "mark_price": mark_price,
        "requested_quote_amount": quote_amount,
        "requested_quantity": explicit_qty if explicit_qty > 0 else None,
        "computed_quantity": qty,
        "computed_notional": notional,
        "filters": filters,
        "filters_ok": filters_ok,
        "min_notional_satisfied": bool(min_notional <= 0 or notional >= min_notional),
        "step_size_satisfied": bool(step_size <= 0 or abs(qty - _floor_to_step(qty, step_size)) < 1e-12),
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "reason_codes": reason_codes,
    }


def _protective_exit_present_from_status(status: dict[str, Any]) -> bool:
    position = _as_dict(status.get("position_snapshot"))
    protective_exit = _as_dict(position.get("protective_exit"))
    risk_plan = _as_dict(position.get("risk_plan"))
    pending = _as_dict(status.get("pending_snapshot"))
    candidates = [protective_exit, risk_plan, pending, _as_dict(status.get("protective_exit")), _as_dict(status.get("risk_plan"))]
    for candidate in candidates:
        if bool(candidate.get("present", False)) or bool(candidate.get("stop_loss_order_id")) or bool(candidate.get("take_profit_order_id")) or bool(candidate.get("protective_exit_present", False)):
            return True
    return False


# --- 4B.4.3.6.6.34-H3 demo entry execution fill-awareness helpers ---
def _object_public_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    for method_name in ("model_dump", "to_dict", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                candidate = method()
            except TypeError:
                continue
            if isinstance(candidate, dict):
                return dict(candidate)
    data: dict[str, Any] = {}
    for name in (
        "ok", "success", "status", "order_id", "orderId", "id",
        "client_order_id", "clientOrderId", "executed_qty", "executedQty",
        "filled_qty", "filledQty", "cum_quote_qty", "cummulativeQuoteQty",
    ):
        if hasattr(value, name):
            try:
                data[name] = getattr(value, name)
            except Exception:
                pass
    return data


def _nested_order_dicts(value: Any) -> list[dict[str, Any]]:
    root = _object_public_dict(value)
    if not root:
        return []
    candidates: list[dict[str, Any]] = [root]
    for key in ("order", "order_result", "result", "response", "data", "raw"):
        nested = root.get(key)
        nested_dict = _object_public_dict(nested)
        if nested_dict:
            candidates.append(nested_dict)
    return candidates


def _first_text_from_dicts(dicts: list[dict[str, Any]], *keys: str) -> str:
    for item in dicts:
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    return ""


def _first_float_from_dicts(dicts: list[dict[str, Any]], *keys: str) -> float:
    for item in dicts:
        for key in keys:
            value = _float_value(item.get(key), 0.0)
            if value > 0:
                return value
    return 0.0


def _position_present_from_status(status: dict[str, Any]) -> bool:
    status = status if isinstance(status, dict) else {}
    candidates = [
        _as_dict(status.get("position_snapshot")),
        _as_dict(status.get("position")),
        _as_dict(status.get("runtime_position")),
        _as_dict(status.get("current_position")),
    ]
    for position in candidates:
        if bool(position.get("present", False)):
            return True
        qty = max(
            _float_value(position.get("qty"), 0.0),
            _float_value(position.get("quantity"), 0.0),
            _float_value(position.get("amount"), 0.0),
            _float_value(position.get("base_qty"), 0.0),
            _float_value(position.get("position_amt"), 0.0),
            _float_value(position.get("positionAmt"), 0.0),
        )
        if abs(qty) > 0:
            return True
    return False


def _pending_order_present_from_status(status: dict[str, Any]) -> bool:
    pending = _as_dict((status if isinstance(status, dict) else {}).get("pending_snapshot"))
    if bool(pending.get("present", False)):
        return True
    for key in ("order_id", "orderId", "client_order_id", "clientOrderId"):
        if pending.get(key):
            return True
    return False


def _build_force_buy_execution_binding(*, result: Any, status_after: dict[str, Any], demo_gate: dict[str, Any], operator_id: str = "UNKNOWN", error: str | None = None) -> dict[str, Any]:
    status_after = status_after if isinstance(status_after, dict) else {}
    dicts = _nested_order_dicts(result)
    status_text = _first_text_from_dicts(dicts, "status", "order_status", "state").upper()
    order_id = _first_text_from_dicts(dicts, "order_id", "orderId", "id")
    client_order_id = _first_text_from_dicts(dicts, "client_order_id", "clientOrderId", "clientOrderID", "client_id")
    executed_qty = _first_float_from_dicts(dicts, "executed_qty", "executedQty", "filled_qty", "filledQty", "qty", "quantity")
    cumulative_quote_qty = _first_float_from_dicts(dicts, "cum_quote_qty", "cummulativeQuoteQty", "cumulative_quote_qty", "quote_qty", "quoteQty")
    position_present = _position_present_from_status(status_after)
    pending_present = _pending_order_present_from_status(status_after)
    protective_exit_present = _protective_exit_present_from_status(status_after)
    explicit_ok = any(bool(item.get("ok", False) or item.get("success", False)) for item in dicts)
    status_accepted = status_text in {"NEW", "PARTIALLY_FILLED", "FILLED", "ACCEPTED", "SUCCESS", "OK"}
    status_terminal_rejected = status_text in {"REJECTED", "EXPIRED", "CANCELED", "CANCELLED", "FAILED"}
    result_has_identifier = bool(order_id or client_order_id)
    result_has_fill = bool(executed_qty > 0 or cumulative_quote_qty > 0 or status_text in {"PARTIALLY_FILLED", "FILLED"})
    result_bound = bool(result_has_identifier or status_text or result_has_fill or position_present or pending_present)
    order_accepted = bool(result_bound and not status_terminal_rejected and (result_has_identifier or status_accepted or result_has_fill or position_present or pending_present or explicit_ok))
    order_executed = bool(result_has_fill or position_present)
    protected_position = bool(position_present and protective_exit_present)
    reason_codes: list[str] = []
    if error:
        reason_codes.append("FORCE_BUY_ENGINE_EXCEPTION")
    if result is None:
        reason_codes.append("FORCE_BUY_RESULT_MISSING")
    if result_bound:
        reason_codes.append("FORCE_BUY_RESULT_BOUND")
    else:
        reason_codes.append("FORCE_BUY_RESULT_NOT_BOUND")
    if order_accepted:
        reason_codes.append("FORCE_BUY_ORDER_ACCEPTED_OR_DETECTED")
    else:
        reason_codes.append("FORCE_BUY_ORDER_NOT_ACCEPTED_OR_DETECTED")
    if order_executed:
        reason_codes.append("FORCE_BUY_FILL_OR_POSITION_DETECTED")
    else:
        reason_codes.append("FORCE_BUY_FILL_NOT_DETECTED")
    if protected_position:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFIED")
    elif position_present:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_MISSING")
    else:
        reason_codes.append("POST_ENTRY_POSITION_NOT_PRESENT")
    if not protected_position:
        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")
    return {
        "contract_version": "4B.4.3.6.6.34-H3",
        "operator_id": str(operator_id or "UNKNOWN"),
        "bound_at_ms": utc_ms(),
        "force_buy_invoked": True,
        "order_result_bound": result_bound,
        "order_accepted": order_accepted,
        "order_executed": order_executed,
        "order_id": order_id or None,
        "client_order_id": client_order_id or None,
        "order_status": status_text or None,
        "executed_qty": executed_qty,
        "cumulative_quote_qty": cumulative_quote_qty,
        "post_entry_position_detected": position_present,
        "pending_order_detected": pending_present,
        "post_entry_protective_exit_verified": protected_position,
        "protective_exit_present": protective_exit_present,
        "authorization_should_be_consumed": order_accepted,
        "no_fill_no_protection_fail_closed": not protected_position,
        "demo_gate_status_before_execution": demo_gate.get("status"),
        "raw_result_type": type(result).__name__ if result is not None else "NoneType",
        "raw_result": _object_public_dict(result),
        "error": error,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "reason_codes": reason_codes,
    }


def _post_entry_protective_exit_record(*, status: dict[str, Any], operator_id: str = "UNKNOWN", latest_execution: dict[str, Any] | None = None) -> dict[str, Any]:
    latest_execution = latest_execution if isinstance(latest_execution, dict) else {}
    position_present = _position_present_from_status(status) or bool(latest_execution.get("post_entry_position_detected", False))
    protective_exit_present = _protective_exit_present_from_status(status) or bool(latest_execution.get("protective_exit_present", False))
    protective_exit_verified = bool(position_present and protective_exit_present)
    reason_codes = ["POST_ENTRY_PROTECTIVE_EXIT_VERIFIED" if protective_exit_verified else "POST_ENTRY_PROTECTIVE_EXIT_NOT_VERIFIED"]
    if not position_present:
        reason_codes.append("POST_ENTRY_POSITION_NOT_PRESENT")
    if latest_execution and not protective_exit_verified:
        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")
    return {
        "contract_version": "4B.4.3.6.6.34-H3",
        "operator_id": str(operator_id or "UNKNOWN"),
        "verified_at_ms": utc_ms(),
        "position_present": position_present,
        "protective_exit_present": protective_exit_present,
        "protective_exit_verified": protective_exit_verified,
        "latest_force_buy_execution_present": bool(latest_execution),
        "read_only": True,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "reason_codes": reason_codes,
    }
# --- end 4B.4.3.6.6.34-H3 helpers ---



def _demo_entry_runtime_awareness_from_status(*, settings: Any, status: dict[str, Any]) -> dict[str, Any]:
    """Build the runtime-awareness contract required by the 33L config audit.

    34 must not call build_exchange_environment_config_audit without runtime_awareness.
    The helper is read-only and only normalizes status/config fields for demo-entry gate evaluation.
    """
    status = status if isinstance(status, dict) else {}
    symbol = str(
        status.get("symbol")
        or _safe_setting_text(settings, "symbol", "trading_symbol", "default_symbol")
        or "UNKNOWN"
    ).upper()
    base_asset, quote_asset = _infer_assets(symbol, {})
    position = _as_dict(status.get("position_snapshot"))
    pending = _as_dict(status.get("pending_snapshot"))
    balance_review = _as_dict(status.get("balance_review"))
    if balance_review:
        base_asset = str(balance_review.get("base_asset") or base_asset or "UNKNOWN").upper()
        quote_asset = str(balance_review.get("quote_asset") or quote_asset or "UNKNOWN").upper()
    return {
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "position_present": bool(position.get("present", False)),
        "pending_present": bool(pending.get("present", False)),
        "risk_badge": str(status.get("risk_badge") or status.get("risk") or "UNKNOWN"),
    }

def _entry_guard_ready_for_demo_entry(*, entry_guard: dict[str, Any], cache_reconciliation: dict[str, Any]) -> bool:
    # 34-H2: recognize the 33M stabilized guard release while remaining fail-closed.
    entry_guard = entry_guard if isinstance(entry_guard, dict) else {}
    cache_reconciliation = cache_reconciliation if isinstance(cache_reconciliation, dict) else {}
    risk_badge = str(entry_guard.get("risk_badge") or "UNKNOWN").upper()
    explicit_available = bool(
        entry_guard.get("entry_actions_enabled", False)
        and not entry_guard.get("force_buy_disabled", False)
        and not entry_guard.get("entry_block_until_reconciled", False)
        and risk_badge == "GREEN"
    )
    explicit_release = bool(
        entry_guard.get("entry_guard_release_verified", False)
        or entry_guard.get("entry_guard_release_authorized", False)
        or entry_guard.get("manual_external_recovery_verified", False)
    )
    stabilized_release = bool(
        cache_reconciliation.get("runtime_snapshot_override_active", False)
        and cache_reconciliation.get("stale_engine_balance_invalidated", False)
        and cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False)
        and cache_reconciliation.get("no_mismatch_from_verified_fresh_source", False)
        and risk_badge == "GREEN"
    )
    return bool(explicit_available and (explicit_release or stabilized_release))


def build_demo_entry_execution_gate_snapshot(*, settings: Any, status: dict[str, Any], entry_guard: dict[str, Any], source_gate: dict[str, Any], cache_reconciliation: dict[str, Any], state: dict[str, Any] | None) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    now = utc_ms()
    runtime_awareness = _demo_entry_runtime_awareness_from_status(settings=settings, status=status)
    config_audit = build_exchange_environment_config_audit(settings, runtime_awareness=runtime_awareness)
    demo_runtime = _is_demo_spot_runtime(settings) and bool(config_audit.get("config_environment_consistent", False))
    latest_dry_run = _as_dict(state.get("latest_dry_run"))
    latest_filter_review = _as_dict(state.get("latest_filter_review")) or _as_dict(latest_dry_run.get("filter_review"))
    latest_intent = _as_dict(state.get("latest_intent"))
    authorization = _as_dict(state.get("demo_trade_authorization"))
    post_entry = _as_dict(state.get("post_entry_protective_exit_verification"))
    latest_execution = _as_dict(state.get("latest_force_buy_execution"))
    auth_expires = _float_value(authorization.get("expires_at_ms"), 0.0)
    authorization_valid = bool(authorization.get("authorized", False) and auth_expires >= now and not authorization.get("consumed", False))
    force_buy_result_bound = bool(latest_execution.get("order_result_bound", False))
    force_buy_order_accepted = bool(latest_execution.get("order_accepted", False))
    force_buy_order_executed = bool(latest_execution.get("order_executed", False))
    post_entry_position_detected = bool(post_entry.get("position_present", False) or latest_execution.get("post_entry_position_detected", False))
    post_entry_protective_exit_verified = bool(post_entry.get("protective_exit_verified", False) or latest_execution.get("post_entry_protective_exit_verified", False))
    execution_attempted = bool(latest_execution)
    no_fill_no_protection_fail_closed = bool(execution_attempted and not post_entry_protective_exit_verified)
    dry_run_ok = bool(latest_dry_run.get("dry_run_passed", False))
    filters_ok = bool(latest_filter_review.get("filters_ok", False))
    intent_recorded = bool(latest_intent.get("intent_recorded", False))
    entry_guard_ready = _entry_guard_ready_for_demo_entry(entry_guard=entry_guard, cache_reconciliation=cache_reconciliation)
    cache_ready = bool(cache_reconciliation.get("runtime_snapshot_override_active", False) and cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False))
    fresh_source_verified = bool(source_gate.get("no_mismatch_from_verified_fresh_source", False) or cache_reconciliation.get("no_mismatch_from_verified_fresh_source", False))
    demo_trade_enablement_ready = bool(demo_runtime and entry_guard_ready and cache_ready and fresh_source_verified and dry_run_ok and filters_ok and intent_recorded and authorization_valid and not no_fill_no_protection_fail_closed)
    reason_codes: list[str] = []
    if demo_runtime:
        reason_codes.append("DEMO_SPOT_LIVE_DEMO_RUNTIME_CONFIRMED")
    else:
        reason_codes.append("DEMO_SPOT_LIVE_DEMO_RUNTIME_NOT_CONFIRMED")
    if entry_guard_ready:
        reason_codes.append("ENTRY_GUARD_RELEASE_VERIFIED")
    else:
        reason_codes.append("ENTRY_GUARD_RELEASE_NOT_VERIFIED")
    if cache_ready:
        reason_codes.append("RUNTIME_CACHE_RECONCILED_FROM_VERIFIED_FRESH_SOURCE")
    else:
        reason_codes.append("RUNTIME_CACHE_RECONCILIATION_NOT_READY")
    if dry_run_ok:
        reason_codes.append("ENTRY_ACTION_DRY_RUN_PASSED")
    else:
        reason_codes.append("ENTRY_ACTION_DRY_RUN_REQUIRED")
    if filters_ok:
        reason_codes.append("ENTRY_FILTERS_VERIFIED")
    else:
        reason_codes.append("ENTRY_FILTERS_NOT_VERIFIED")
    if intent_recorded:
        reason_codes.append("ORDER_INTENT_AUDIT_RECORDED")
    else:
        reason_codes.append("ORDER_INTENT_AUDIT_REQUIRED")
    if authorization_valid:
        reason_codes.append("DEMO_ONLY_TRADE_AUTHORIZATION_VALID")
    elif authorization:
        reason_codes.append("DEMO_ONLY_TRADE_AUTHORIZATION_EXPIRED_OR_CONSUMED")
    else:
        reason_codes.append("DEMO_ONLY_TRADE_AUTHORIZATION_REQUIRED")
    if post_entry_protective_exit_verified:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFIED")
    elif no_fill_no_protection_fail_closed:
        reason_codes.append("NO_FILL_NO_PROTECTION_FAIL_CLOSED")
    else:
        reason_codes.append("POST_ENTRY_PROTECTIVE_EXIT_VERIFICATION_PENDING")
    return {
        "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
        "enabled": True,
        "entry_action_dry_run_enabled": True,
        "min_notional_step_size_verification_enabled": True,
        "order_intent_audit_enabled": True,
        "demo_only_trade_enablement_enabled": True,
        "post_entry_protective_exit_verification_enabled": True,
        "demo_spot_live_demo_runtime_confirmed": demo_runtime,
        "entry_guard_ready": entry_guard_ready,
        "cache_reconciliation_ready": cache_ready,
        "fresh_source_no_mismatch_verified": fresh_source_verified,
        "dry_run_passed": dry_run_ok,
        "filters_verified": filters_ok,
        "intent_recorded": intent_recorded,
        "demo_trade_authorization_valid": authorization_valid,
        "demo_trade_enablement_ready": demo_trade_enablement_ready,
        "latest_dry_run": latest_dry_run,
        "latest_filter_review": latest_filter_review,
        "latest_intent": latest_intent,
        "demo_trade_authorization": authorization,
        "post_entry_protective_exit_verification": post_entry,
        "force_buy_execution_fill_awareness_version": "4B.4.3.6.6.34-H3",
        "latest_force_buy_execution": latest_execution,
        "force_buy_result_bound": force_buy_result_bound,
        "force_buy_order_accepted": force_buy_order_accepted,
        "force_buy_order_executed": force_buy_order_executed,
        "post_entry_position_detected": post_entry_position_detected,
        "post_entry_protective_exit_verified": post_entry_protective_exit_verified,
        "no_fill_no_protection_fail_closed": no_fill_no_protection_fail_closed,
        "engine_position_state_mutated": False,
        "auto_position_mutation_performed": False,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "reason_codes": reason_codes,
        "status": "DEMO_ENTRY_EXECUTION_PROTECTED" if post_entry_protective_exit_verified else ("DEMO_ENTRY_EXECUTION_FAIL_CLOSED_NO_PROTECTION" if no_fill_no_protection_fail_closed else ("DEMO_ENTRY_ENABLEMENT_READY" if demo_trade_enablement_ready else "WAITING_FOR_DEMO_ENTRY_EXECUTION_PREFLIGHT")),
    }
# --- end 4B.4.3.6.6.34 helpers ---


def build_entry_guard_visibility(runtime_awareness: dict[str, Any], runtime_lock: dict[str, Any], startup_error: str | None, risk_reconciliation: dict[str, Any] | None = None, reconciliation_execution: dict[str, Any] | None = None, engine_position_recovery_gate: dict[str, Any] | None = None, external_recovery_evidence_gate: dict[str, Any] | None = None, exchange_environment_source_gate: dict[str, Any] | None = None) -> dict[str, Any]:
    reason_codes: list[str] = []
    manual_recovery_verified = bool(
        engine_position_recovery_gate
        and external_recovery_evidence_gate
        and exchange_environment_source_gate
        and engine_position_recovery_gate.get("entry_guard_release_verified", False)
        and external_recovery_evidence_gate.get("entry_guard_release_verified", False)
        and exchange_environment_source_gate.get("entry_guard_release_verified", False)
    )
    release_authorized = bool((reconciliation_execution and reconciliation_execution.get("entry_guard_release_authorized", False)) or manual_recovery_verified)
    if not release_authorized and str(runtime_awareness.get("risk_badge") or "").upper() == "RED":
        reason_codes.append("RED_RISK_BADGE_ENTRY_GUARD")
    if not release_authorized and bool(runtime_awareness.get("base_balance_present_position_not_tracked", False)):
        reason_codes.append("BASE_BALANCE_PRESENT_POSITION_NOT_TRACKED")
    if not release_authorized and bool(runtime_awareness.get("orphan_local_position_recovery_detected", False)):
        reason_codes.append("ORPHAN_RECOVERY_REQUIRES_OPERATOR_REVIEW")
    if not release_authorized and risk_reconciliation and bool(risk_reconciliation.get("entry_blocked_until_reconciled", False)):
        reason_codes.append("ENTRY_BLOCK_UNTIL_RECONCILED")
    if startup_error:
        reason_codes.append("COCKPIT_STARTUP_ERROR_PRESENT")
    if engine_position_recovery_gate and not bool(engine_position_recovery_gate.get("entry_guard_release_verified", False)) and bool(engine_position_recovery_gate.get("requires_manual_external_recovery", False)):
        reason_codes.append("ENGINE_POSITION_RECOVERY_NOT_VERIFIED")
    if external_recovery_evidence_gate and not bool(external_recovery_evidence_gate.get("entry_guard_release_verified", False)) and bool(engine_position_recovery_gate and engine_position_recovery_gate.get("requires_manual_external_recovery", False)):
        reason_codes.append("EXTERNAL_RECOVERY_EVIDENCE_NOT_VERIFIED")
    if exchange_environment_source_gate and not bool(exchange_environment_source_gate.get("entry_guard_release_verified", False)) and bool(engine_position_recovery_gate and engine_position_recovery_gate.get("requires_manual_external_recovery", False)):
        reason_codes.append("EXCHANGE_ENVIRONMENT_SOURCE_NOT_VERIFIED")
    if bool(runtime_lock.get("duplicate_instance_blocked", False)):
        reason_codes.append("DUPLICATE_COCKPIT_INSTANCE_BLOCKED")
    force_buy_disabled = bool(reason_codes)
    return {
        "contract_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
        "entry_guard_visibility_enabled": True,
        "always_on_entry_guard_snapshot": True,
        "force_buy_disabled": force_buy_disabled,
        "entry_actions_enabled": not force_buy_disabled,
        "entry_block_until_reconciled": bool(risk_reconciliation and risk_reconciliation.get("entry_blocked_until_reconciled", False)),
        "reconciled": bool(risk_reconciliation and risk_reconciliation.get("reconciled", False)),
        "manual_acknowledgement_allows_entry": False,
        "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
        "entry_guard_release_authorized": release_authorized,
        "manual_external_recovery_verified": manual_recovery_verified,
        "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
        "risk_badge": runtime_awareness.get("risk_badge"),
        "reason_codes": reason_codes,
        "disable_reason": ", ".join(reason_codes) if reason_codes else "ENTRY_ACTIONS_AVAILABLE",
        "message": "Entry actions are blocked until balance/position reconciliation is resolved." if force_buy_disabled else "Entry actions available.",
    }


class TradeBotOrchestrator:
    """Single-process control plane for TradeBot V2 Operator Cockpit."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = SQLiteStore(settings.database_path)
        self.engine = TradeBotEngine(settings, self.store)
        self.process_started_at_ms = utc_ms()
        self.last_heartbeat_ms = self.process_started_at_ms
        self.engine_started_at_ms: int | None = None
        self.engine_stopped_at_ms: int | None = None
        self.last_shutdown_reason: str | None = None
        self._psutil_process = psutil.Process(os.getpid()) if psutil is not None else None
        if self._psutil_process is not None:
            try:
                self._psutil_process.cpu_percent(interval=None)
            except Exception:
                pass
        self._runtime_lock: RuntimeLockHandle | None = None
        self._startup_error: str | None = None
        self._last_runtime_lock_diagnostic: dict[str, Any] = inspect_runtime_lock(settings, None)
        self._shutdown_lock = asyncio.Lock()

    @property
    def startup_error(self) -> str | None:
        return self._startup_error

    @property
    def runtime_lock_present(self) -> bool:
        return bool(self._runtime_lock is not None or inspect_runtime_lock(self.settings, self._runtime_lock).get("exists", False))

    @property
    def runtime_lock_held_by_current_process(self) -> bool:
        return self._runtime_lock is not None

    async def open(self) -> None:
        """Prepare cockpit resources without starting order-producing logic."""
        if not bool(getattr(self.settings, "runtime_lock_enabled", True)):
            self._last_runtime_lock_diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)
            return
        if self._runtime_lock is not None:
            self._last_runtime_lock_diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)
            return
        identity = f"cockpit:{getattr(self.settings, 'symbol', 'UNKNOWN')}:{os.getpid()}"
        try:
            self._runtime_lock = acquire_runtime_lock(
                getattr(self.settings, "runtime_lock_path", ".tradebot/runtime.lock"),
                identity=identity,
                stale_after_seconds=0,
            )
            self._startup_error = None
        except Exception as exc:  # fail-safe: cockpit starts degraded, engine start stays blocked
            self._startup_error = f"RUNTIME_LOCK_BLOCKED: {exc}"
        self._last_runtime_lock_diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)

    async def shutdown(self) -> None:
        async with self._shutdown_lock:
            self.last_shutdown_reason = "COCKPIT_SHUTDOWN"
            try:
                await self.stop_engine(reason="COCKPIT_SHUTDOWN")
            finally:
                try:
                    await self.engine.close()
                finally:
                    if self._runtime_lock is not None:
                        release_runtime_lock(self._runtime_lock)
                        self._runtime_lock = None
                    self._last_runtime_lock_diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)
                    close = getattr(self.store, "close", None)
                    if callable(close):
                        close()

    def _result(self, *, ok: bool, action: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return CockpitActionResult(ok=ok, action=action, message=message, data=data or {}).to_dict()

    async def start_engine(self) -> dict[str, Any]:
        if self._startup_error:
            return self._result(ok=False, action="engine.start", message="Cockpit runtime lock is not available", data={"startup_error": self._startup_error, "runtime_lock": inspect_runtime_lock(self.settings, self._runtime_lock)})
        try:
            started = await self.engine.start()
            if bool(started):
                self.engine_started_at_ms = utc_ms()
                self.engine_stopped_at_ms = None
            return self._result(ok=True, action="engine.start", message="Engine start requested", data={"started": bool(started), "already_running": not bool(started), "engine_started_at_ms": self.engine_started_at_ms})
        except Exception as exc:
            return self._result(ok=False, action="engine.start", message="Engine start failed", data={"error": str(exc)})

    async def stop_engine(self, *, reason: str = "OPERATOR_STOP") -> dict[str, Any]:
        self.last_shutdown_reason = reason
        try:
            stopped = await self.engine.stop()
            if bool(stopped):
                self.engine_stopped_at_ms = utc_ms()
            return self._result(ok=True, action="engine.stop", message="Engine stop requested", data={"stopped": bool(stopped), "already_stopped": not bool(stopped), "reason": reason, "engine_stopped_at_ms": self.engine_stopped_at_ms})
        except Exception as exc:
            return self._result(ok=False, action="engine.stop", message="Engine stop failed", data={"error": str(exc), "reason": reason})

    async def restart_engine(self) -> dict[str, Any]:
        stop_result = await self.stop_engine(reason="OPERATOR_RESTART")
        start_result = await self.start_engine()
        return self._result(ok=bool(stop_result.get("ok") and start_result.get("ok")), action="engine.restart", message="Engine restart requested", data={"stop": stop_result, "start": start_result})

    async def _entry_guard_snapshot(self) -> dict[str, Any]:
        try:
            status = await self.engine.get_status()
        except Exception:
            status = {}
        try:
            logs = self.store.fetch_logs(limit=80, order="desc")
        except Exception:
            logs = []
        awareness = build_runtime_awareness_snapshot(status, logs)
        runtime_lock = inspect_runtime_lock(self.settings, self._runtime_lock)
        balance_review = build_balance_review_snapshot(status, awareness)
        reconciliation = build_risk_reconciliation_snapshot(
            status=status,
            runtime_awareness=awareness,
            balance_review=balance_review,
            acknowledgement=self._risk_reconciliation_acknowledgement(),
        )
        adoption_candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        execution = build_reconciliation_execution_snapshot(
            runtime_awareness=awareness,
            balance_review=balance_review,
            risk_reconciliation=reconciliation,
            decision=self._risk_reconciliation_decision(),
            adoption_candidate=adoption_candidate,
        )
        decision_apply = build_reconciliation_decision_apply_snapshot(reconciliation_execution=execution, decision=self._risk_reconciliation_decision())
        recovery_gate = build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=decision_apply, recovery_plan=self._engine_position_recovery_plan())
        return build_entry_guard_visibility(awareness, runtime_lock, self._startup_error, reconciliation, execution, recovery_gate)

    def _risk_reconciliation_acknowledgement(self) -> dict[str, Any] | None:
        value = _safe_store_get_json(self.store, _reconciliation_key(self.settings), None)
        return value if isinstance(value, dict) else None

    def _risk_reconciliation_decision(self) -> dict[str, Any] | None:
        value = _safe_store_get_json(self.store, _reconciliation_decision_key(self.settings), None)
        return value if isinstance(value, dict) else None

    def _engine_position_recovery_plan(self) -> dict[str, Any] | None:
        value = _safe_store_get_json(self.store, _engine_position_recovery_key(self.settings), None)
        return value if isinstance(value, dict) else None


    def _demo_entry_execution_state(self) -> dict[str, Any]:
        value = _safe_store_get_json(self.store, _demo_entry_execution_key(self.settings), {})
        return value if isinstance(value, dict) else {}

    def _set_demo_entry_execution_state(self, state: dict[str, Any]) -> bool:
        return _safe_store_set_json(self.store, _demo_entry_execution_key(self.settings), state)

    async def _demo_entry_execution_gate_snapshot_from_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return build_demo_entry_execution_gate_snapshot(
            settings=self.settings,
            status=_as_dict(snapshot.get("status")),
            entry_guard=_as_dict(snapshot.get("entry_guard")),
            source_gate=_as_dict(snapshot.get("exchange_environment_source_gate")),
            cache_reconciliation=_as_dict(snapshot.get("engine_status_balance_cache_reconciliation")),
            state=self._demo_entry_execution_state(),
        )

    async def demo_entry_dry_run(self, *, operator_id: str = "UNKNOWN", spec: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        gate_before = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
        filter_review = _build_demo_entry_filter_review(_as_dict(snapshot.get("status")), self.settings, spec)
        dry_run_passed = bool(
            gate_before.get("demo_spot_live_demo_runtime_confirmed", False)
            and gate_before.get("entry_guard_ready", False)
            and gate_before.get("cache_reconciliation_ready", False)
            and gate_before.get("fresh_source_no_mismatch_verified", False)
            and filter_review.get("filters_ok", False)
        )
        record = {
            "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "created_at_ms": utc_ms(),
            "dry_run_passed": dry_run_passed,
            "filter_review": filter_review,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "order_path_mutation_performed": False,
            "live_real_enablement_performed": False,
            "reason_codes": [
                "ENTRY_ACTION_DRY_RUN_PASSED" if dry_run_passed else "ENTRY_ACTION_DRY_RUN_BLOCKED",
                *list(filter_review.get("reason_codes", [])),
            ],
        }
        state = self._demo_entry_execution_state()
        state["latest_dry_run"] = record
        state["latest_filter_review"] = filter_review
        state["demo_trade_authorization"] = {}
        ledger = list(state.get("dry_run_ledger") or [])
        ledger.append(record)
        state["dry_run_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=dry_run_passed, action="demo_entry.dry_run", message="34 demo entry dry-run passed." if dry_run_passed else "34 demo entry dry-run blocked; filters or recovery gates are not satisfied.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "dry_run": record})

    async def verify_demo_entry_filters(self, *, operator_id: str = "UNKNOWN", spec: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        filter_review = _build_demo_entry_filter_review(_as_dict(snapshot.get("status")), self.settings, spec)
        state = self._demo_entry_execution_state()
        state["latest_filter_review"] = filter_review
        state["filter_review_operator_id"] = str(operator_id or "UNKNOWN")
        state["filter_review_at_ms"] = utc_ms()
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        ok = bool(filter_review.get("filters_ok", False))
        return self._result(ok=ok, action="demo_entry.verify_filters", message="34 min-notional and step-size verification passed." if ok else "34 min-notional or step-size verification blocked.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "filter_review": filter_review})

    async def record_demo_entry_intent(self, *, operator_id: str = "UNKNOWN", intent: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self._demo_entry_execution_state()
        latest_dry_run = _as_dict(state.get("latest_dry_run"))
        latest_filter_review = _as_dict(state.get("latest_filter_review"))
        intent = intent if isinstance(intent, dict) else {}
        intent_recorded = bool(latest_dry_run.get("dry_run_passed", False) and latest_filter_review.get("filters_ok", False))
        record = {
            "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "recorded_at_ms": utc_ms(),
            "intent_recorded": intent_recorded,
            "symbol": str(intent.get("symbol") or latest_filter_review.get("symbol") or getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "side": str(intent.get("side") or latest_filter_review.get("side") or "BUY").upper(),
            "quantity": _float_value(intent.get("quantity"), _float_value(latest_filter_review.get("computed_quantity"), 0.0)),
            "notional": _float_value(intent.get("notional"), _float_value(latest_filter_review.get("computed_notional"), 0.0)),
            "dry_run_reference_ms": latest_dry_run.get("created_at_ms"),
            "filter_review": latest_filter_review,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "order_path_mutation_performed": False,
            "live_real_enablement_performed": False,
            "reason_codes": ["ORDER_INTENT_AUDIT_RECORDED" if intent_recorded else "ORDER_INTENT_AUDIT_BLOCKED_DRY_RUN_REQUIRED"],
        }
        state["latest_intent"] = record
        state["demo_trade_authorization"] = {}
        ledger = list(state.get("intent_ledger") or [])
        ledger.append(record)
        state["intent_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=intent_recorded, action="demo_entry.record_intent", message="34 demo entry order intent audit recorded." if intent_recorded else "34 intent audit blocked; a passing dry-run and filter review are required.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "intent": record})

    async def authorize_demo_only_entry(self, *, operator_id: str = "UNKNOWN", ttl_seconds: int = 120) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
        state = self._demo_entry_execution_state()
        latest_intent = _as_dict(state.get("latest_intent"))
        ttl_ms = max(min(int(ttl_seconds), 600), 10) * 1000
        now = utc_ms()
        authorized = bool(
            gate.get("demo_spot_live_demo_runtime_confirmed", False)
            and gate.get("entry_guard_ready", False)
            and gate.get("cache_reconciliation_ready", False)
            and gate.get("fresh_source_no_mismatch_verified", False)
            and gate.get("dry_run_passed", False)
            and gate.get("filters_verified", False)
            and latest_intent.get("intent_recorded", False)
        )
        record = {
            "contract_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "authorized_at_ms": now,
            "expires_at_ms": now + ttl_ms,
            "authorized": authorized,
            "consumed": False,
            "demo_only": True,
            "intent": latest_intent,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "order_path_mutation_performed": False,
            "live_real_enablement_performed": False,
            "reason_codes": ["DEMO_ONLY_TRADE_AUTHORIZATION_VALID" if authorized else "DEMO_ONLY_TRADE_AUTHORIZATION_BLOCKED"],
        }
        state["demo_trade_authorization"] = record
        ledger = list(state.get("authorization_ledger") or [])
        ledger.append(record)
        state["authorization_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=authorized, action="demo_entry.authorize_demo_only_entry", message="34 demo-only entry authorization recorded." if authorized else "34 demo-only entry authorization blocked by preflight.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "authorization": record})

    async def verify_post_entry_protective_exit(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        try:
            status = await self.engine.get_status()
        except Exception as exc:
            status = {"ok": False, "error": str(exc)}
        state = self._demo_entry_execution_state()
        latest_execution = _as_dict(state.get("latest_force_buy_execution"))
        record = _post_entry_protective_exit_record(status=status, operator_id=operator_id, latest_execution=latest_execution)
        protective_exit_verified = bool(record.get("protective_exit_verified", False))
        state["post_entry_protective_exit_verification"] = record
        ledger = list(state.get("post_entry_protective_exit_ledger") or [])
        ledger.append(record)
        state["post_entry_protective_exit_ledger"] = ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        return self._result(ok=protective_exit_verified, action="demo_entry.verify_post_entry_protective_exit", message="34-H3 post-entry protective exit verified." if protective_exit_verified else "34-H3 post-entry protective exit is not verified; no-fill/no-protection gate remains fail-closed.", data={"demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "post_entry_protective_exit_verification": record})

    async def clear_demo_entry_execution_gate(self) -> dict[str, Any]:
        saved = self._set_demo_entry_execution_state({})
        return self._result(ok=bool(saved), action="demo_entry.clear", message="34 demo entry execution gate cleared; new dry-run and intent audit are required before demo entry.", data={"cleared_at_ms": utc_ms(), "cleared": bool(saved)})

    async def acknowledge_risk_reconciliation(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        try:
            status = await self.engine.get_status()
        except Exception:
            status = {}
        try:
            logs = self.store.fetch_logs(limit=80, order="desc")
        except Exception:
            logs = []
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        payload = {
            "contract_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "acknowledged_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "risk_badge": awareness.get("risk_badge"),
            "reason_codes": list(awareness.get("reason_codes") or []),
            "base_asset": awareness.get("base_asset"),
            "tradable_base": awareness.get("tradable_base"),
            "position_present": awareness.get("position_present"),
            "base_balance_present_position_not_tracked": awareness.get("base_balance_present_position_not_tracked"),
            "acknowledgement_allows_entry": False,
            "entry_remains_blocked_until_reconciled": True,
            "balance_review": balance_review,
        }
        saved = _safe_store_set_json(self.store, _reconciliation_key(self.settings), payload)
        reconciliation = build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=payload)
        return self._result(ok=bool(saved), action="risk_reconciliation.acknowledge", message="Risk reconciliation review acknowledged; entry remains blocked until mismatch is resolved.", data={"acknowledgement": payload, "risk_reconciliation": reconciliation})

    async def clear_risk_reconciliation_acknowledgement(self) -> dict[str, Any]:
        saved = _safe_store_set_json(self.store, _reconciliation_key(self.settings), {})
        return self._result(ok=bool(saved), action="risk_reconciliation.clear_acknowledgement", message="Risk reconciliation acknowledgement cleared.", data={"contract_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION, "cleared_at_ms": utc_ms(), "cleared": True})

    async def confirm_balance_snapshot(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        decision = {
            "contract_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "decision_type": "BALANCE_SNAPSHOT_CONFIRMED",
            "operator_id": str(operator_id or "UNKNOWN"),
            "decided_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "balance_review": balance_review,
            "entry_guard_release_requested": False,
            "entry_guard_release_authorized": False,
        }
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), decision)
        return self._result(ok=bool(saved), action="risk_reconciliation.confirm_balance_snapshot", message="Read-only balance snapshot confirmed; entry remains blocked until reconciliation clear.", data={"decision": decision})

    async def resolve_dust_safe_base_balance(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        reconciliation = build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement())
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        draft_decision = {
            "contract_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "decision_type": "DUST_SAFE_BASE_BALANCE_RESOLUTION",
            "operator_id": str(operator_id or "UNKNOWN"),
            "decided_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "balance_review": balance_review,
            "entry_guard_release_requested": True,
        }
        execution = build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=reconciliation, decision=draft_decision, adoption_candidate=candidate)
        draft_decision["entry_guard_release_authorized"] = bool(execution.get("entry_guard_release_authorized", False))
        draft_decision["dust_safe_eligible"] = bool(execution.get("dust_safe_eligible", False))
        draft_decision["execution_reason_codes"] = list(execution.get("reason_codes") or [])
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), draft_decision)
        return self._result(ok=bool(saved and execution.get("dust_safe_eligible", False)), action="risk_reconciliation.resolve_dust_safe", message="Dust-safe reconciliation decision recorded." if execution.get("dust_safe_eligible", False) else "Dust-safe reconciliation rejected; base balance is not dust-safe.", data={"decision": draft_decision, "reconciliation_execution": execution})

    async def create_tracked_position_adoption_candidate(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        decision = {
            "contract_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "decision_type": "TRACKED_POSITION_ADOPTION_CANDIDATE",
            "operator_id": str(operator_id or "UNKNOWN"),
            "decided_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "candidate": candidate,
            "engine_position_state_mutated": False,
            "entry_guard_release_requested": False,
            "entry_guard_release_authorized": False,
        }
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), decision)
        return self._result(ok=bool(saved and candidate.get("candidate_available", False)), action="risk_reconciliation.adopt_position_candidate", message="Tracked position adoption candidate recorded; engine state was not mutated and entry remains blocked until actual reconciliation clear.", data={"decision": decision})


    async def apply_tracked_position_candidate_review(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        decision = {
            "contract_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "decision_type": "TRACKED_POSITION_CANDIDATE_REVIEWED",
            "operator_id": str(operator_id or "UNKNOWN"),
            "decided_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "candidate": candidate,
            "tracked_position_candidate_reviewed": True,
            "engine_position_state_mutated": False,
            "requires_separate_engine_position_recovery": True,
            "entry_guard_release_requested": False,
            "entry_guard_release_authorized": False,
        }
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), decision)
        return self._result(
            ok=bool(saved and candidate.get("candidate_available", False)),
            action="risk_reconciliation.apply_tracked_position_candidate_review",
            message="Tracked position candidate review recorded; engine state was not mutated and entry remains blocked until recovery is actually clear.",
            data={"decision": decision, "candidate": candidate},
        )

    async def apply_dust_safe_clear(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        reconciliation = build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement())
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        decision = {
            "contract_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "decision_type": "DUST_SAFE_CLEAR_APPLIED",
            "operator_id": str(operator_id or "UNKNOWN"),
            "decided_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "balance_review": balance_review,
            "engine_position_state_mutated": False,
            "entry_guard_release_requested": True,
        }
        execution = build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=reconciliation, decision=decision, adoption_candidate=candidate)
        decision["entry_guard_release_authorized"] = bool(execution.get("entry_guard_release_authorized", False))
        decision["dust_safe_eligible"] = bool(execution.get("dust_safe_eligible", False))
        decision["execution_reason_codes"] = list(execution.get("reason_codes") or [])
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), decision)
        return self._result(
            ok=bool(saved and execution.get("entry_guard_release_authorized", False)),
            action="risk_reconciliation.apply_dust_safe_clear",
            message="Dust-safe clear applied and entry guard release verified." if execution.get("entry_guard_release_authorized", False) else "Dust-safe clear rejected; base balance is not dust-safe and entry remains blocked.",
            data={"decision": decision, "reconciliation_execution": execution},
        )

    async def clear_manual_reconciliation_decision(self) -> dict[str, Any]:
        saved = _safe_store_set_json(self.store, _reconciliation_decision_key(self.settings), {})
        return self._result(ok=bool(saved), action="risk_reconciliation.clear_manual_decision", message="Manual reconciliation decision cleared; entry guard will re-evaluate from live read-only state.", data={"cleared_at_ms": utc_ms(), "cleared": True})

    async def resolve_runtime_lock_owner_mismatch(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)
        resolver = build_runtime_lock_owner_mismatch_resolver(diagnostic, self._startup_error)
        if bool(diagnostic.get("held_by_current_process", False)):
            self._startup_error = None
            return self._result(ok=True, action="runtime_lock.resolve_owner_mismatch", message="Runtime lock already held by current process.", data={"resolver": resolver, "runtime_lock": diagnostic})
        if not bool(resolver.get("safe_clear_allowed", False)):
            return self._result(ok=False, action="runtime_lock.resolve_owner_mismatch", message="Runtime lock owner mismatch is not safe to resolve automatically; stop duplicate instances or restart cleanly.", data={"resolver": resolver, "runtime_lock": diagnostic, "operator_id": operator_id})
        try:
            Path(str(diagnostic.get("path") or _runtime_lock_path(self.settings))).unlink(missing_ok=True)
            identity = f"cockpit:{getattr(self.settings, 'symbol', 'UNKNOWN')}:{os.getpid()}"
            self._runtime_lock = acquire_runtime_lock(getattr(self.settings, "runtime_lock_path", ".tradebot/runtime.lock"), identity=identity, stale_after_seconds=0)
            self._startup_error = None
            updated = inspect_runtime_lock(self.settings, self._runtime_lock)
            self._last_runtime_lock_diagnostic = updated
            return self._result(ok=True, action="runtime_lock.resolve_owner_mismatch", message="Stale runtime lock owner mismatch resolved and lock reacquired by current process.", data={"resolver": build_runtime_lock_owner_mismatch_resolver(updated, self._startup_error), "runtime_lock": updated, "operator_id": operator_id})
        except Exception as exc:
            updated = inspect_runtime_lock(self.settings, self._runtime_lock)
            self._last_runtime_lock_diagnostic = updated
            self._startup_error = f"RUNTIME_LOCK_RESOLVE_FAILED: {exc}"
            return self._result(ok=False, action="runtime_lock.resolve_owner_mismatch", message="Runtime lock owner mismatch resolver failed.", data={"error": str(exc), "resolver": build_runtime_lock_owner_mismatch_resolver(updated, self._startup_error), "runtime_lock": updated, "operator_id": operator_id})


    async def create_engine_position_recovery_plan(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        reconciliation = build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement())
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        execution = build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=reconciliation, decision=self._risk_reconciliation_decision(), adoption_candidate=candidate)
        apply_snapshot = build_reconciliation_decision_apply_snapshot(reconciliation_execution=execution, decision=self._risk_reconciliation_decision())
        decision_type = str(apply_snapshot.get("decision_type") or "NONE")
        reviewed = bool(decision_type == "TRACKED_POSITION_CANDIDATE_REVIEWED" and candidate.get("candidate_available", False))
        plan = {
            "contract_version": OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
            "legacy_gate_version": OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION,
            "plan_type": "MANUAL_EXTERNAL_ENGINE_POSITION_RECOVERY_PLAN",
            "operator_id": str(operator_id or "UNKNOWN"),
            "created_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "candidate": candidate,
            "reviewed_candidate_required": True,
            "reviewed_candidate_present": reviewed,
            "plan_confirmed": False,
            "manual_external_recovery_confirmed": False,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "requires_manual_external_recovery": True,
            "entry_guard_release_requested": False,
            "entry_guard_release_authorized": False,
            "entry_guard_release_verified": False,
            "verified_no_mismatch": False,
            "recovery_actions_required": [
                "Review exchange/account inventory outside the bot.",
                "Resolve the base-balance/position mismatch outside automatic order entry.",
                "Do not enable new BUY until a fresh read-only cockpit snapshot verifies no active mismatch.",
                "Record verification through the 33J recovery completion gate.",
            ],
            "allowed_resolution_modes": [
                "MANUAL_EXTERNAL_POSITION_RECONSTRUCTION",
                "MANUAL_EXTERNAL_BALANCE_LIQUIDATION_OR_TRANSFER",
                "MANUAL_ACCOUNTING_RECONCILIATION_WITH_NO_ACTIVE_MISMATCH",
            ],
        }
        saved = _safe_store_set_json(self.store, _engine_position_recovery_key(self.settings), plan) if reviewed else False
        gate = build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=apply_snapshot, recovery_plan=plan if reviewed else {})
        return self._result(
            ok=bool(saved and reviewed),
            action="engine_position_recovery.create_plan",
            message="33J recovery plan created from reviewed candidate; engine state was not mutated and entry remains blocked." if reviewed else "Recovery plan rejected; tracked position candidate review decision is required first.",
            data={"recovery_plan": plan if reviewed else {}, "engine_position_recovery_gate": gate, "recovery_plan_apply_verification_gate": gate.get("recovery_plan_apply_verification_gate")},
        )

    async def create_recovery_plan_from_reviewed_candidate(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        result = await self.create_engine_position_recovery_plan(operator_id=operator_id)
        result["action"] = "recovery_plan_apply.create_from_reviewed_candidate"
        if result.get("ok"):
            result["message"] = "Recovery plan apply gate created from reviewed candidate; no engine position state was mutated."
        return result

    async def confirm_engine_position_recovery_plan(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        plan = self._engine_position_recovery_plan() or {}
        if not plan:
            return self._result(ok=False, action="engine_position_recovery.confirm_plan", message="No engine position recovery plan is present.", data={"recovery_plan": {}})
        plan = dict(plan)
        plan["plan_confirmed"] = True
        plan["manual_external_recovery_confirmed"] = True
        plan["confirmed_by"] = str(operator_id or "UNKNOWN")
        plan["confirmed_at_ms"] = utc_ms()
        plan["manual_external_recovery_confirmation"] = {
            "contract_version": OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "confirmed_at_ms": plan["confirmed_at_ms"],
            "attestation": "Operator confirms recovery will be performed externally/manually and not by automatic cockpit position mutation.",
        }
        plan["engine_position_state_mutated"] = False
        plan["auto_position_mutation_performed"] = False
        plan["entry_guard_release_authorized"] = False
        plan["entry_guard_release_verified"] = False
        saved = _safe_store_set_json(self.store, _engine_position_recovery_key(self.settings), plan)
        return self._result(ok=bool(saved), action="engine_position_recovery.confirm_plan", message="33J manual external recovery plan confirmed; perform recovery outside this gate and verify no-mismatch afterwards.", data={"recovery_plan": plan})

    async def confirm_manual_external_recovery_plan(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        result = await self.confirm_engine_position_recovery_plan(operator_id=operator_id)
        result["action"] = "recovery_plan_apply.confirm_manual_external_recovery"
        return result

    async def verify_engine_position_recovery_completion(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        plan = self._engine_position_recovery_plan() or {}
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        reconciliation = build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement())
        candidate = build_tracked_position_adoption_candidate(status, awareness, balance_review)
        execution = build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=reconciliation, decision=self._risk_reconciliation_decision(), adoption_candidate=candidate)
        apply_snapshot = build_reconciliation_decision_apply_snapshot(reconciliation_execution=execution, decision=self._risk_reconciliation_decision())
        gate_before = build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=apply_snapshot, recovery_plan=plan)
        plan_confirmed = bool(plan.get("plan_confirmed", False))
        manual_external_confirmed = bool(plan.get("manual_external_recovery_confirmed", False))
        mismatch_active = bool(awareness.get("base_balance_present_position_not_tracked", False))
        orphan_active = bool(awareness.get("orphan_local_position_recovery_detected", False))
        position_present = bool(awareness.get("position_present", False))
        verified_no_mismatch = bool(plan_confirmed and manual_external_confirmed and not mismatch_active and not orphan_active)
        engine_position_verified = bool(verified_no_mismatch and position_present)
        empty_inventory_verified = bool(verified_no_mismatch and not position_present)
        plan = dict(plan)
        plan["verification"] = {
            "contract_version": OPERATOR_COCKPIT_RECOVERY_PLAN_APPLY_VERIFICATION_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "verified_at_ms": utc_ms(),
            "plan_confirmed": plan_confirmed,
            "manual_external_recovery_confirmed": manual_external_confirmed,
            "position_present": position_present,
            "mismatch_active": mismatch_active,
            "orphan_recovery_detected": orphan_active,
            "verified_no_mismatch": verified_no_mismatch,
            "engine_position_verified": engine_position_verified,
            "empty_inventory_verified": empty_inventory_verified,
            "entry_guard_release_verified": verified_no_mismatch,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "reason_codes": gate_before.get("reason_codes", []),
        }
        completion_ledger = list(plan.get("recovery_completion_ledger") or [])
        completion_ledger.append(plan["verification"])
        plan["recovery_completion_ledger"] = completion_ledger[-20:]
        plan["verified_no_mismatch"] = verified_no_mismatch
        plan["engine_position_verified"] = engine_position_verified
        plan["empty_inventory_verified"] = empty_inventory_verified
        plan["entry_guard_release_authorized"] = verified_no_mismatch
        plan["entry_guard_release_verified"] = verified_no_mismatch
        plan["engine_position_state_mutated"] = False
        plan["auto_position_mutation_performed"] = False
        saved = _safe_store_set_json(self.store, _engine_position_recovery_key(self.settings), plan)
        gate_after = build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=apply_snapshot, recovery_plan=plan)
        return self._result(
            ok=bool(saved and verified_no_mismatch),
            action="engine_position_recovery.verify_completion",
            message="33J recovery verified no-mismatch; entry guard may re-evaluate from live state." if verified_no_mismatch else "33J recovery not verified; live mismatch/orphan condition is still active or plan confirmation is missing.",
            data={"recovery_plan": plan, "engine_position_recovery_gate": gate_after, "recovery_plan_apply_verification_gate": gate_after.get("recovery_plan_apply_verification_gate")},
        )

    async def verify_recovery_no_mismatch(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        result = await self.verify_engine_position_recovery_completion(operator_id=operator_id)
        result["action"] = "recovery_plan_apply.verify_no_mismatch"
        return result

    async def clear_engine_position_recovery_plan(self) -> dict[str, Any]:
        saved = _safe_store_set_json(self.store, _engine_position_recovery_key(self.settings), {})
        return self._result(ok=bool(saved), action="engine_position_recovery.clear_plan", message="33J recovery plan cleared; entry guard remains governed by live mismatch state.", data={"cleared_at_ms": utc_ms(), "cleared": True})

    async def clear_recovery_plan_apply(self) -> dict[str, Any]:
        result = await self.clear_engine_position_recovery_plan()
        result["action"] = "recovery_plan_apply.clear"
        return result


    def _external_recovery_evidence_state(self) -> dict[str, Any]:
        value = _safe_store_get_json(self.store, _external_recovery_evidence_key(self.settings), {})
        return value if isinstance(value, dict) else {}


    def _exchange_environment_source_gate_state(self) -> dict[str, Any]:
        value = _safe_store_get_json(self.store, _exchange_environment_source_gate_key(self.settings), {})
        return value if isinstance(value, dict) else {}

    async def verify_exchange_environment_consistency(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=awareness, balance_review=balance_review, source_state=self._exchange_environment_source_gate_state())
        audit = source_gate.get("config_audit", {})
        ok = bool(isinstance(audit, dict) and audit.get("config_environment_consistent", False))
        return self._result(ok=ok, action="exchange_environment.verify_consistency", message="33L exchange environment config audit passed." if ok else "33L exchange environment config audit failed or is incomplete.", data={"exchange_environment_source_gate": source_gate, "operator_id": operator_id})

    async def capture_fresh_exchange_balance_source(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        _, base_asset, quote_asset = _symbol_assets_from_settings(self.settings, awareness)
        dust_floor = _float_value(_as_dict(balance_review.get("base")).get("dust"))
        fresh = await fetch_fresh_exchange_balance_source(self.engine, self.settings, base_asset=base_asset, quote_asset=quote_asset, dust_floor=dust_floor)
        record = {
            "contract_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "captured_at_ms": utc_ms(),
            "ok": bool(fresh.get("ok", False)),
            "source_object": fresh.get("source_object"),
            "source_method": fresh.get("source_method"),
            "balances": fresh.get("balances") or {},
            "attempts": fresh.get("attempts") or [],
            "error": fresh.get("error"),
            "engine_balance_source": _as_dict(balance_review.get("base")).get("source"),
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
        }
        state = self._exchange_environment_source_gate_state()
        ledger = list(state.get("fresh_balance_source_ledger") or [])
        ledger.append(record)
        state["fresh_balance_source"] = record
        state["fresh_balance_source_ledger"] = ledger[-20:]
        saved = _safe_store_set_json(self.store, _exchange_environment_source_gate_key(self.settings), state)
        source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=awareness, balance_review=balance_review, source_state=state)
        return self._result(ok=bool(saved and source_gate.get("fresh_exchange_balance_verified", False)), action="exchange_environment.capture_fresh_balance", message="33L fresh exchange balance source verified." if source_gate.get("fresh_exchange_balance_verified", False) else "33L fresh exchange balance source could not be verified; no-mismatch remains blocked.", data={"exchange_environment_source_gate": source_gate, "fresh_balance_source": record})

    async def verify_recovery_no_mismatch_from_fresh_exchange_source(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        plan = self._engine_position_recovery_plan() or {}
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=awareness, balance_review=balance_review, source_state=self._exchange_environment_source_gate_state())
        evidence_gate = build_external_recovery_evidence_gate_snapshot(runtime_awareness=awareness, engine_position_recovery_gate=build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=build_reconciliation_decision_apply_snapshot(reconciliation_execution=build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement()), decision=self._risk_reconciliation_decision(), adoption_candidate=build_tracked_position_adoption_candidate(status, awareness, balance_review)), decision=self._risk_reconciliation_decision()), recovery_plan=plan), evidence_state=self._external_recovery_evidence_state(), exchange_environment_source_gate=source_gate)
        verified = bool(
            source_gate.get("no_mismatch_from_verified_fresh_source", False)
            and evidence_gate.get("evidence_complete", False)
            and evidence_gate.get("post_recovery_snapshot_fresh", False)
            and plan.get("plan_confirmed", False)
            and plan.get("manual_external_recovery_confirmed", False)
        )
        plan = dict(plan)
        verification = {
            "contract_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "verified_at_ms": utc_ms(),
            "verified_from_fresh_exchange_source": verified,
            "verified_no_mismatch": verified,
            "entry_guard_release_verified": verified,
            "exchange_environment_source_gate": source_gate,
            "evidence_gate": evidence_gate,
            "engine_status_balance_source_rejected": bool(source_gate.get("engine_status_balance_source_rejected", False)),
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
        }
        plan["verification"] = verification
        ledger = list(plan.get("recovery_completion_ledger") or [])
        ledger.append(verification)
        plan["recovery_completion_ledger"] = ledger[-20:]
        plan["verified_no_mismatch"] = verified
        plan["engine_position_verified"] = bool(verified and awareness.get("position_present", False))
        plan["empty_inventory_verified"] = bool(verified and not awareness.get("position_present", False))
        plan["entry_guard_release_authorized"] = verified
        plan["entry_guard_release_verified"] = verified
        plan["engine_position_state_mutated"] = False
        plan["auto_position_mutation_performed"] = False
        saved = _safe_store_set_json(self.store, _engine_position_recovery_key(self.settings), plan)
        return self._result(ok=bool(saved and verified), action="exchange_environment.verify_no_mismatch_from_fresh_source", message="33L recovery verified from fresh exchange balance source." if verified else "33L recovery not verified; fresh exchange balance source does not prove no-mismatch.", data={"recovery_plan": plan, "exchange_environment_source_gate": source_gate, "external_recovery_evidence_gate": evidence_gate, "verification": verification})

    async def clear_exchange_environment_source_gate(self) -> dict[str, Any]:
        saved = _safe_store_set_json(self.store, _exchange_environment_source_gate_key(self.settings), {})
        return self._result(ok=bool(saved), action="exchange_environment.clear", message="33L exchange environment source gate cleared; no-mismatch verification remains fail-closed until fresh source is verified.", data={"cleared_at_ms": utc_ms(), "cleared": True})


    async def capture_external_recovery_evidence(self, *, operator_id: str = "UNKNOWN", evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self._external_recovery_evidence_state()
        evidence = dict(evidence or {})
        mode = str(evidence.get("recovery_mode") or evidence.get("mode") or "MANUAL_EXTERNAL_POSITION_RECONSTRUCTION").strip().upper()
        allowed_modes = {
            "MANUAL_EXTERNAL_POSITION_RECONSTRUCTION",
            "MANUAL_EXTERNAL_BALANCE_LIQUIDATION_OR_TRANSFER",
            "MANUAL_ACCOUNTING_RECONCILIATION_WITH_NO_ACTIVE_MISMATCH",
        }
        if mode not in allowed_modes:
            mode = "MANUAL_EXTERNAL_POSITION_RECONSTRUCTION"
        plan = self._engine_position_recovery_plan() or {}
        record = {
            "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "captured_at_ms": utc_ms(),
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "recovery_mode": mode,
            "operator_attestation": str(evidence.get("operator_attestation") or evidence.get("attestation") or "Operator attests that external/manual recovery evidence has been reviewed."),
            "external_reference": str(evidence.get("external_reference") or evidence.get("reference") or "LOCAL_OPERATOR_EVIDENCE"),
            "notes": str(evidence.get("notes") or ""),
            "plan_present": bool(plan),
            "plan_confirmed": bool(plan.get("plan_confirmed", False)),
            "manual_external_recovery_confirmed": bool(plan.get("manual_external_recovery_confirmed", False)),
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
        }
        ledger = list(state.get("evidence_ledger") or [])
        ledger.append(record)
        state["latest_evidence"] = record
        state["evidence_ledger"] = ledger[-20:]
        saved = _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), state)
        snapshot = await self.snapshot(log_limit=20)
        gate = snapshot.get("external_recovery_evidence_gate") or {}
        return self._result(ok=bool(saved), action="external_recovery_evidence.capture", message="33K external recovery evidence captured; entry remains blocked until fresh no-mismatch verification passes.", data={"external_recovery_evidence_gate": gate, "evidence": record})

    async def capture_post_recovery_balance_snapshot(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        state = self._external_recovery_evidence_state()
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        record = {
            "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "captured_at_ms": utc_ms(),
            "read_only": True,
            "symbol": str(getattr(self.settings, "symbol", "UNKNOWN") or "UNKNOWN").upper(),
            "risk_badge": awareness.get("risk_badge"),
            "position_present": bool(awareness.get("position_present", False)),
            "mismatch_active": bool(awareness.get("base_balance_present_position_not_tracked", False)),
            "orphan_recovery_detected": bool(awareness.get("orphan_local_position_recovery_detected", False)),
            "balance_review": balance_review,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
        }
        ledger = list(state.get("post_recovery_snapshot_ledger") or [])
        ledger.append(record)
        state["post_recovery_snapshot"] = record
        state["post_recovery_snapshot_ledger"] = ledger[-20:]
        saved = _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), state)
        snapshot = await self.snapshot(log_limit=20)
        gate = snapshot.get("external_recovery_evidence_gate") or {}
        return self._result(ok=bool(saved), action="external_recovery_evidence.capture_post_recovery_snapshot", message="33K read-only post-recovery snapshot captured; no engine position state was mutated.", data={"external_recovery_evidence_gate": gate, "post_recovery_snapshot": record})

    async def run_external_recovery_no_mismatch_preflight(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        state = self._external_recovery_evidence_state()
        status = await self.engine.get_status() if hasattr(self.engine, "get_status") else {}
        logs = self.store.fetch_logs(limit=80, order="desc")
        awareness = build_runtime_awareness_snapshot(status, logs)
        balance_review = build_balance_review_snapshot(status, awareness)
        recovery_gate = build_engine_position_recovery_gate_snapshot(runtime_awareness=awareness, reconciliation_decision_apply=build_reconciliation_decision_apply_snapshot(reconciliation_execution=build_reconciliation_execution_snapshot(runtime_awareness=awareness, balance_review=balance_review, risk_reconciliation=build_risk_reconciliation_snapshot(status=status, runtime_awareness=awareness, balance_review=balance_review, acknowledgement=self._risk_reconciliation_acknowledgement()), decision=self._risk_reconciliation_decision(), adoption_candidate=build_tracked_position_adoption_candidate(status, awareness, balance_review)), decision=self._risk_reconciliation_decision()), recovery_plan=self._engine_position_recovery_plan())
        source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=awareness, balance_review=balance_review, source_state=self._exchange_environment_source_gate_state())
        evidence_gate = build_external_recovery_evidence_gate_snapshot(runtime_awareness=awareness, engine_position_recovery_gate=recovery_gate, evidence_state=state, exchange_environment_source_gate=source_gate)
        preflight_passed = bool(
            evidence_gate.get("evidence_complete", False)
            and evidence_gate.get("post_recovery_snapshot_fresh", False)
            and source_gate.get("no_mismatch_from_verified_fresh_source", False)
            and evidence_gate.get("plan_confirmed", False)
            and evidence_gate.get("manual_external_recovery_confirmed", False)
        )
        record = {
            "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "checked_at_ms": utc_ms(),
            "preflight_passed": preflight_passed,
            "fresh_snapshot_required": True,
            "evidence_required": True,
            "mismatch_active": bool(evidence_gate.get("mismatch_active", True)),
            "orphan_recovery_detected": bool(evidence_gate.get("orphan_recovery_detected", True)),
            "post_recovery_snapshot_fresh": bool(evidence_gate.get("post_recovery_snapshot_fresh", False)),
            "evidence_complete": bool(evidence_gate.get("evidence_complete", False)),
            "fresh_exchange_balance_verified": bool(source_gate.get("fresh_exchange_balance_verified", False)),
            "no_mismatch_from_verified_fresh_source": bool(source_gate.get("no_mismatch_from_verified_fresh_source", False)),
            "engine_status_balance_source_rejected": bool(source_gate.get("engine_status_balance_source_rejected", False)),
            "exchange_environment_source_gate": source_gate,
            "plan_confirmed": bool(evidence_gate.get("plan_confirmed", False)),
            "manual_external_recovery_confirmed": bool(evidence_gate.get("manual_external_recovery_confirmed", False)),
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "reason_codes": evidence_gate.get("reason_codes", []),
        }
        ledger = list(state.get("preflight_ledger") or [])
        ledger.append(record)
        state["no_mismatch_preflight"] = record
        state["preflight_ledger"] = ledger[-20:]
        saved = _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), state)
        snapshot = await self.snapshot(log_limit=20)
        gate = snapshot.get("external_recovery_evidence_gate") or {}
        return self._result(ok=bool(saved and preflight_passed), action="external_recovery_evidence.no_mismatch_preflight", message="33K no-mismatch preflight passed." if preflight_passed else "33K no-mismatch preflight blocked; evidence, fresh snapshot, or no-mismatch condition is not satisfied.", data={"external_recovery_evidence_gate": gate, "no_mismatch_preflight": record})

    async def verify_no_mismatch_safe_apply_with_evidence(self, *, operator_id: str = "UNKNOWN") -> dict[str, Any]:
        preflight_result = await self.run_external_recovery_no_mismatch_preflight(operator_id=operator_id)
        state = self._external_recovery_evidence_state()
        preflight = _as_dict(state.get("no_mismatch_preflight"))
        if not bool(preflight.get("preflight_passed", False)):
            record = {
                "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
                "operator_id": str(operator_id or "UNKNOWN"),
                "applied_at_ms": utc_ms(),
                "verified_no_mismatch_with_evidence": False,
                "entry_guard_release_verified": False,
                "blocked_by_preflight": True,
                "engine_position_state_mutated": False,
                "auto_position_mutation_performed": False,
                "preflight": preflight,
            }
            state["verify_no_mismatch_safe_apply"] = record
            _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), state)
            snapshot = await self.snapshot(log_limit=20)
            return self._result(ok=False, action="external_recovery_evidence.verify_no_mismatch_safe_apply", message="33K safe apply blocked; no-mismatch preflight has not passed.", data={"external_recovery_evidence_gate": snapshot.get("external_recovery_evidence_gate"), "verify_no_mismatch_safe_apply": record, "preflight_result": preflight_result})
        verify_result = await self.verify_recovery_no_mismatch_from_fresh_exchange_source(operator_id=operator_id)
        verified = bool(verify_result.get("ok", False))
        record = {
            "contract_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "operator_id": str(operator_id or "UNKNOWN"),
            "applied_at_ms": utc_ms(),
            "verified_no_mismatch_with_evidence": verified,
            "entry_guard_release_verified": verified,
            "engine_position_state_mutated": False,
            "auto_position_mutation_performed": False,
            "preflight": preflight,
            "verification_result_ok": verified,
            "verified_from_fresh_exchange_source": verified,
        }
        state["verify_no_mismatch_safe_apply"] = record
        ledger = list(state.get("safe_apply_ledger") or [])
        ledger.append(record)
        state["safe_apply_ledger"] = ledger[-20:]
        _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), state)
        snapshot = await self.snapshot(log_limit=20)
        gate = snapshot.get("external_recovery_evidence_gate") or {}
        return self._result(ok=verified, action="external_recovery_evidence.verify_no_mismatch_safe_apply", message="33K verified no-mismatch with evidence and fresh snapshot." if verified else "33K safe apply failed after preflight; entry remains blocked.", data={"external_recovery_evidence_gate": gate, "verify_no_mismatch_safe_apply": record, "verification_result": verify_result})

    async def clear_external_recovery_evidence(self) -> dict[str, Any]:
        saved = _safe_store_set_json(self.store, _external_recovery_evidence_key(self.settings), {})
        return self._result(ok=bool(saved), action="external_recovery_evidence.clear", message="33K external recovery evidence cleared; entry guard remains fail-closed until evidence and fresh no-mismatch verification are present.", data={"cleared_at_ms": utc_ms(), "cleared": True})

    async def force_buy(self) -> dict[str, Any]:
        snapshot = await self.snapshot(log_limit=20)
        guard = _as_dict(snapshot.get("entry_guard"))
        if bool(guard.get("force_buy_disabled", False)):
            reason_code = "ENTRY_BLOCK_UNTIL_RECONCILED" if bool(guard.get("entry_block_until_reconciled", False)) else "RED_RISK_BADGE_ENTRY_GUARD"
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by cockpit entry guard", data={"reason_code": reason_code, "entry_guard": guard})
        demo_gate = await self._demo_entry_execution_gate_snapshot_from_snapshot(snapshot)
        if not bool(demo_gate.get("demo_trade_enablement_ready", False)):
            return self._result(ok=False, action="trade.force_buy", message="Force BUY blocked by 34 demo entry execution gate; run dry-run, filters, intent audit, and demo-only authorization first.", data={"reason_code": "DEMO_ENTRY_EXECUTION_GATE_NOT_READY", "entry_guard": guard, "demo_entry_execution_gate": demo_gate})
        result: Any = None
        error_text: str | None = None
        try:
            result = await self.engine.force_buy()
        except Exception as exc:
            error_text = str(exc)
        try:
            status_after = await self.engine.get_status()
        except Exception as exc:
            status_after = {"ok": False, "error": str(exc)}
        state = self._demo_entry_execution_state()
        binding = _build_force_buy_execution_binding(result=result, status_after=status_after, demo_gate=demo_gate, operator_id=_as_dict(state.get("demo_trade_authorization")).get("operator_id") or "UNKNOWN", error=error_text)
        authorization = _as_dict(state.get("demo_trade_authorization"))
        if authorization and bool(binding.get("authorization_should_be_consumed", False)):
            authorization["consumed"] = True
            authorization["consumed_at_ms"] = utc_ms()
            authorization["consumption_reason"] = "FORCE_BUY_ORDER_ACCEPTED_OR_DETECTED"
            state["demo_trade_authorization"] = authorization
        elif authorization:
            authorization["consumption_blocked_reason"] = "FORCE_BUY_RESULT_NOT_BOUND_OR_NOT_ACCEPTED"
            state["demo_trade_authorization"] = authorization
        state["latest_force_buy_execution"] = binding
        ledger = list(state.get("force_buy_execution_ledger") or [])
        ledger.append(binding)
        state["force_buy_execution_ledger"] = ledger[-30:]
        post_entry_record = _post_entry_protective_exit_record(status=status_after, operator_id=binding.get("operator_id") or "UNKNOWN", latest_execution=binding)
        state["post_entry_protective_exit_verification"] = post_entry_record
        post_ledger = list(state.get("post_entry_protective_exit_ledger") or [])
        post_ledger.append(post_entry_record)
        state["post_entry_protective_exit_ledger"] = post_ledger[-30:]
        self._set_demo_entry_execution_state(state)
        snapshot_after = await self.snapshot(log_limit=20)
        ok = bool(binding.get("order_result_bound", False) and binding.get("order_accepted", False) and binding.get("post_entry_protective_exit_verified", False))
        if error_text:
            message = "34-H3 Force BUY failed in engine execution path."
            reason_code = "FORCE_BUY_ENGINE_EXCEPTION"
        elif ok:
            message = "34-H3 Force BUY bound to accepted order and protected post-entry state."
            reason_code = "FORCE_BUY_ORDER_BOUND_AND_PROTECTED"
        else:
            message = "34-H3 Force BUY is fail-closed: order/fill/protective-exit binding is incomplete."
            reason_code = "FORCE_BUY_NO_FILL_NO_PROTECTION_FAIL_CLOSED"
        return self._result(ok=ok, action="trade.force_buy", message=message, data={"reason_code": reason_code, "entry_guard": guard, "demo_entry_execution_gate": snapshot_after.get("demo_entry_execution_gate"), "force_buy_execution": binding, "post_entry_protective_exit_verification": post_entry_record})

    async def force_sell(self) -> dict[str, Any]:
        try:
            await self.engine.force_sell()
            return self._result(ok=True, action="trade.force_sell", message="Force SELL requested")
        except Exception as exc:
            return self._result(ok=False, action="trade.force_sell", message="Force SELL failed", data={"error": str(exc)})

    async def cancel_pending(self) -> dict[str, Any]:
        try:
            await self.engine.cancel_pending(reason="COCKPIT_OPERATOR_CANCEL")
            return self._result(ok=True, action="trade.cancel_pending", message="Pending cancel requested")
        except Exception as exc:
            return self._result(ok=False, action="trade.cancel_pending", message="Pending cancel failed", data={"error": str(exc)})

    async def risk_reset(self) -> dict[str, Any]:
        try:
            await self.engine.risk_reset()
            return self._result(ok=True, action="risk.reset", message="Risk counters reset")
        except Exception as exc:
            return self._result(ok=False, action="risk.reset", message="Risk reset failed", data={"error": str(exc)})

    async def toggle_safe_mode(self) -> dict[str, Any]:
        try:
            await self.engine.toggle_safe_mode()
            return self._result(ok=True, action="risk.safe_mode.toggle", message="Safe mode toggled")
        except Exception as exc:
            return self._result(ok=False, action="risk.safe_mode.toggle", message="Safe mode toggle failed", data={"error": str(exc)})

    async def clear_stale_runtime_lock(self) -> dict[str, Any]:
        diagnostic = inspect_runtime_lock(self.settings, self._runtime_lock)
        if self._runtime_lock is not None:
            return self._result(ok=False, action="runtime_lock.clear_stale", message="Current cockpit already owns the runtime lock", data={"runtime_lock": diagnostic, "reason_code": "CURRENT_PROCESS_OWNS_RUNTIME_LOCK"})
        if not diagnostic.get("exists", False):
            await self.open()
            return self._result(ok=True, action="runtime_lock.clear_stale", message="No stale runtime lock file exists; lock acquisition retried", data={"runtime_lock": inspect_runtime_lock(self.settings, self._runtime_lock)})
        if not diagnostic.get("stale_reclaim_safe", False):
            return self._result(ok=False, action="runtime_lock.clear_stale", message="Runtime lock is not safe to clear", data={"runtime_lock": diagnostic, "reason_code": "RUNTIME_LOCK_CLEAR_NOT_SAFE"})
        path = Path(str(diagnostic.get("path") or _runtime_lock_path(self.settings)))
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            return self._result(ok=False, action="runtime_lock.clear_stale", message="Failed to delete stale runtime lock", data={"error": str(exc), "runtime_lock": diagnostic})
        await self.open()
        return self._result(ok=self._startup_error is None, action="runtime_lock.clear_stale", message="Stale runtime lock cleared and acquisition retried", data={"runtime_lock_before": diagnostic, "runtime_lock_after": inspect_runtime_lock(self.settings, self._runtime_lock), "startup_error": self._startup_error})

    def _process_metrics(self) -> dict[str, Any]:
        if self._psutil_process is None:
            return {"cpu_percent": None, "memory_rss_mb": None, "memory_percent": None, "psutil_available": False}
        try:
            mem = self._psutil_process.memory_info()
            return {
                "cpu_percent": float(self._psutil_process.cpu_percent(interval=None)),
                "memory_rss_mb": round(float(mem.rss) / (1024 * 1024), 2),
                "memory_percent": round(float(self._psutil_process.memory_percent()), 4),
                "psutil_available": True,
            }
        except Exception:
            return {"cpu_percent": None, "memory_rss_mb": None, "memory_percent": None, "psutil_available": False}

    def system_snapshot(self) -> dict[str, Any]:
        now = utc_ms()
        engine_running = bool(getattr(self.engine, "_running", False))
        engine_uptime_sec = None
        if engine_running and self.engine_started_at_ms is not None:
            engine_uptime_sec = max((now - self.engine_started_at_ms) / 1000.0, 0.0)
        metrics = self._process_metrics()
        payload = CockpitSystemSnapshot(
            pid=os.getpid(),
            uptime_sec=max((now - self.process_started_at_ms) / 1000.0, 0.0),
            heartbeat_age_ms=max(now - self.last_heartbeat_ms, 0),
            process_started_at_ms=self.process_started_at_ms,
            now_ms=now,
            engine_running=engine_running,
            engine_started_at_ms=self.engine_started_at_ms,
            engine_uptime_sec=engine_uptime_sec,
            cpu_percent=metrics["cpu_percent"],
            memory_rss_mb=metrics["memory_rss_mb"],
            memory_percent=metrics["memory_percent"],
            psutil_available=bool(metrics["psutil_available"]),
        ).to_dict()
        payload["last_shutdown_reason"] = self.last_shutdown_reason
        payload["engine_stopped_at_ms"] = self.engine_stopped_at_ms
        payload["action_audit_runtime_lock_version"] = OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION
        return payload

    async def snapshot(self, *, log_limit: int = 80) -> dict[str, Any]:
        self.last_heartbeat_ms = utc_ms()
        try:
            status = await self.engine.get_status()
        except Exception as exc:
            status = {"ok": False, "degraded": True, "error": str(exc), "state": "UNKNOWN"}
        try:
            logs = self.store.fetch_logs(limit=max(int(log_limit), 0), order="desc")
        except Exception as exc:
            logs = [{"ts": utc_ms(), "level": "ERROR", "code": "COCKPIT_LOG_FETCH_FAILED", "message": str(exc), "data": {}}]
        runtime_awareness = build_runtime_awareness_snapshot(status, logs)
        runtime_lock = inspect_runtime_lock(self.settings, self._runtime_lock)
        self._last_runtime_lock_diagnostic = runtime_lock
        evidence_state = self._external_recovery_evidence_state()
        balance_review = build_balance_review_snapshot(status, runtime_awareness)
        risk_reconciliation = build_risk_reconciliation_snapshot(
            status=status,
            runtime_awareness=runtime_awareness,
            balance_review=balance_review,
            acknowledgement=self._risk_reconciliation_acknowledgement(),
        )
        tracked_position_adoption_candidate = build_tracked_position_adoption_candidate(status, runtime_awareness, balance_review)
        reconciliation_execution = build_reconciliation_execution_snapshot(
            runtime_awareness=runtime_awareness,
            balance_review=balance_review,
            risk_reconciliation=risk_reconciliation,
            decision=self._risk_reconciliation_decision(),
            adoption_candidate=tracked_position_adoption_candidate,
        )
        reconciliation_decision_apply = build_reconciliation_decision_apply_snapshot(reconciliation_execution=reconciliation_execution, decision=self._risk_reconciliation_decision())
        exchange_environment_source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=runtime_awareness, balance_review=balance_review, source_state=self._exchange_environment_source_gate_state())
        engine_status_balance_cache_reconciliation = build_engine_status_balance_cache_reconciliation_snapshot(
            runtime_awareness=runtime_awareness,
            balance_review=balance_review,
            evidence_state=evidence_state,
            exchange_environment_source_gate=exchange_environment_source_gate,
        )
        if bool(engine_status_balance_cache_reconciliation.get("runtime_snapshot_override_active", False)):
            runtime_awareness, balance_review = apply_engine_status_balance_cache_reconciliation(runtime_awareness, balance_review, engine_status_balance_cache_reconciliation)
            risk_reconciliation = build_risk_reconciliation_snapshot(
                status=status,
                runtime_awareness=runtime_awareness,
                balance_review=balance_review,
                acknowledgement=self._risk_reconciliation_acknowledgement(),
            )
            tracked_position_adoption_candidate = build_tracked_position_adoption_candidate(status, runtime_awareness, balance_review)
            reconciliation_execution = build_reconciliation_execution_snapshot(
                runtime_awareness=runtime_awareness,
                balance_review=balance_review,
                risk_reconciliation=risk_reconciliation,
                decision=self._risk_reconciliation_decision(),
                adoption_candidate=tracked_position_adoption_candidate,
            )
            reconciliation_decision_apply = build_reconciliation_decision_apply_snapshot(reconciliation_execution=reconciliation_execution, decision=self._risk_reconciliation_decision())
            exchange_environment_source_gate = build_exchange_environment_source_gate_snapshot(settings=self.settings, runtime_awareness=runtime_awareness, balance_review=balance_review, source_state=self._exchange_environment_source_gate_state())
        exchange_environment_source_gate = apply_engine_status_balance_cache_reconciliation_to_source_gate(exchange_environment_source_gate, engine_status_balance_cache_reconciliation)
        engine_position_recovery_gate = build_engine_position_recovery_gate_snapshot(runtime_awareness=runtime_awareness, reconciliation_decision_apply=reconciliation_decision_apply, recovery_plan=self._engine_position_recovery_plan())
        external_recovery_evidence_gate = build_external_recovery_evidence_gate_snapshot(runtime_awareness=runtime_awareness, engine_position_recovery_gate=engine_position_recovery_gate, evidence_state=evidence_state, exchange_environment_source_gate=exchange_environment_source_gate)
        if bool(exchange_environment_source_gate.get("entry_guard_release_verified", False)) and bool(external_recovery_evidence_gate.get("entry_guard_release_verified", False)):
            engine_position_recovery_gate["entry_guard_release_verified"] = True
            engine_position_recovery_gate["verified_no_mismatch"] = True
            engine_position_recovery_gate["external_recovery_verified"] = True
            engine_position_recovery_gate["requires_manual_external_recovery"] = False
            engine_position_recovery_gate["exchange_environment_source_gate_version"] = OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION
            engine_position_recovery_gate["engine_status_balance_cache_reconciliation_version"] = OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION
            engine_position_recovery_gate["engine_status_balance_cache_reconciliation"] = engine_status_balance_cache_reconciliation
            engine_position_recovery_gate.setdefault("reason_codes", []).append("ENTRY_GUARD_RELEASE_VERIFIED_FROM_FRESH_EXCHANGE_SOURCE")
            engine_position_recovery_gate.setdefault("reason_codes", []).append("ENTRY_GUARD_RELEASE_STABILIZED_AFTER_SAFE_APPLY")
        elif not bool(external_recovery_evidence_gate.get("entry_guard_release_verified", False)) and bool(engine_position_recovery_gate.get("requires_manual_external_recovery", False)):
            engine_position_recovery_gate["entry_guard_release_verified"] = False
            engine_position_recovery_gate["external_recovery_evidence_required"] = True
            engine_position_recovery_gate["external_recovery_evidence_gate_version"] = OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION
            engine_position_recovery_gate["exchange_environment_source_gate_required"] = True
            engine_position_recovery_gate["exchange_environment_source_gate_version"] = OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION
        runtime_lock_owner_mismatch_resolver = build_runtime_lock_owner_mismatch_resolver(runtime_lock, self._startup_error)
        entry_guard = build_entry_guard_visibility(runtime_awareness, runtime_lock, self._startup_error, risk_reconciliation, reconciliation_execution, engine_position_recovery_gate, external_recovery_evidence_gate, exchange_environment_source_gate)
        runtime_awareness["entry_guard"] = entry_guard
        runtime_awareness["risk_reconciliation"] = risk_reconciliation
        runtime_awareness["balance_review"] = balance_review
        runtime_awareness["reconciliation_execution"] = reconciliation_execution
        runtime_awareness["reconciliation_decision_apply"] = reconciliation_decision_apply
        runtime_awareness["tracked_position_adoption_candidate"] = tracked_position_adoption_candidate
        runtime_awareness["runtime_lock_owner_mismatch_resolver"] = runtime_lock_owner_mismatch_resolver
        runtime_awareness["engine_position_recovery_gate"] = engine_position_recovery_gate
        runtime_awareness["recovery_plan_apply_verification_gate"] = engine_position_recovery_gate.get("recovery_plan_apply_verification_gate")
        runtime_awareness["external_recovery_evidence_gate"] = external_recovery_evidence_gate
        runtime_awareness["exchange_environment_source_gate"] = exchange_environment_source_gate
        runtime_awareness["engine_status_balance_cache_reconciliation"] = engine_status_balance_cache_reconciliation
        demo_entry_execution_gate = build_demo_entry_execution_gate_snapshot(settings=self.settings, status=status, entry_guard=entry_guard, source_gate=exchange_environment_source_gate, cache_reconciliation=engine_status_balance_cache_reconciliation, state=self._demo_entry_execution_state())
        runtime_awareness["demo_entry_execution_gate"] = demo_entry_execution_gate
        operator_actions = fetch_recent_operator_actions(self.store, limit=80)
        operator_action_summary = summarize_operator_actions(operator_actions)
        security_snapshot = build_security_snapshot(self.settings)
        system = self.system_snapshot()
        return {
            "ok": self._startup_error is None,
            "contract_version": OPERATOR_COCKPIT_CONTRACT_VERSION,
            "runtime_hardening_version": OPERATOR_COCKPIT_RUNTIME_HARDENING_VERSION,
            "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
            "ux_health_version": OPERATOR_COCKPIT_UX_HEALTH_VERSION,
            "action_audit_runtime_lock_version": OPERATOR_COCKPIT_ACTION_AUDIT_RUNTIME_LOCK_VERSION,
            "risk_reconciliation_version": OPERATOR_COCKPIT_RISK_RECONCILIATION_VERSION,
            "reconciliation_execution_version": OPERATOR_COCKPIT_RECONCILIATION_EXECUTION_VERSION,
            "reconciliation_decision_apply_version": OPERATOR_COCKPIT_RECONCILIATION_DECISION_APPLY_VERSION,
            "engine_position_recovery_gate_version": OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_GATE_VERSION,
            "external_recovery_evidence_gate_version": OPERATOR_COCKPIT_EXTERNAL_RECOVERY_EVIDENCE_GATE_VERSION,
            "exchange_environment_source_gate_version": OPERATOR_COCKPIT_EXCHANGE_ENVIRONMENT_SOURCE_GATE_VERSION,
            "engine_status_balance_cache_reconciliation_version": OPERATOR_COCKPIT_ENGINE_STATUS_BALANCE_CACHE_RECONCILIATION_VERSION,
            "demo_entry_execution_control_version": OPERATOR_COCKPIT_DEMO_ENTRY_EXECUTION_CONTROL_VERSION,
            "cockpit": {
                "name": "TradeBot V2 Operator Cockpit",
                "foundation_enabled": True,
                "runtime_hardening_enabled": True,
                "security_gate_enabled": True,
                "ux_health_observability_enabled": True,
                "action_audit_runtime_lock_enabled": True,
                "risk_reconciliation_enabled": True,
                "reconciliation_execution_enabled": True,
                "reconciliation_decision_apply_enabled": True,
                "engine_position_recovery_gate_enabled": True,
                "external_recovery_evidence_gate_enabled": True,
                "exchange_environment_source_gate_enabled": True,
                "demo_entry_execution_control_enabled": True,
                "runtime_lock_present": bool(runtime_lock.get("exists", False) or self._runtime_lock is not None),
                "runtime_lock_held_by_current_process": bool(self._runtime_lock is not None),
                "startup_error": self._startup_error,
                "last_shutdown_reason": self.last_shutdown_reason,
                "duplicate_cockpit_instance_blocked": bool(runtime_lock.get("duplicate_instance_blocked", False)),
                "stale_lock_diagnostic_available": bool(runtime_lock.get("exists", False)),
            },
            "security": security_snapshot,
            "runtime_awareness": runtime_awareness,
            "runtime_lock": runtime_lock,
            "entry_guard": entry_guard,
            "balance_review": balance_review,
            "risk_reconciliation": risk_reconciliation,
            "reconciliation_execution": reconciliation_execution,
            "reconciliation_decision_apply": reconciliation_decision_apply,
            "engine_position_recovery_gate": engine_position_recovery_gate,
            "external_recovery_evidence_gate": external_recovery_evidence_gate,
            "exchange_environment_source_gate": exchange_environment_source_gate,
            "engine_status_balance_cache_reconciliation": engine_status_balance_cache_reconciliation,
            "demo_entry_execution_gate": demo_entry_execution_gate,
            "tracked_position_adoption_candidate": tracked_position_adoption_candidate,
            "operator_actions": operator_actions,
            "operator_action_ledger": operator_action_summary,
            "engine_running": bool(getattr(self.engine, "_running", False)),
            "status": status,
            "logs": logs,
            "system": system,
        }

# --- 4B.4.3.6.6.33I-H1 engine position recovery persistence key hotfix ---
def _engine_position_recovery_key(settings):
    """Return the persistence key used by the 33I recovery gate.

    The 33I snapshot path calls this helper while reading the recovery plan.
    It must be present at module scope before runtime snapshot/WebSocket paths are used.
    The key is symbol-scoped to prevent cross-symbol recovery-plan leakage.
    """
    symbol = getattr(settings, "symbol", None)
    if not symbol:
        symbol = getattr(settings, "trading_symbol", None)
    if not symbol:
        symbol = getattr(settings, "default_symbol", None)
    symbol_text = str(symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    return f"operator_cockpit:engine_position_recovery:{symbol_text}"
# --- end 4B.4.3.6.6.33I-H1 ---


def _external_recovery_evidence_key(settings):
    """Return the symbol-scoped persistence key used by the 33K evidence gate."""
    symbol = getattr(settings, "symbol", None) or getattr(settings, "trading_symbol", None) or getattr(settings, "default_symbol", None)
    symbol_text = str(symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    return f"operator_cockpit:external_recovery_evidence:{symbol_text}"



def _exchange_environment_source_gate_key(settings):
    """Return the symbol-scoped persistence key used by the 33L source gate."""
    symbol = getattr(settings, "symbol", None) or getattr(settings, "trading_symbol", None) or getattr(settings, "default_symbol", None)
    symbol_text = str(symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    return f"operator_cockpit:exchange_environment_source_gate:{symbol_text}"


# --- 4B.4.3.6.6.34 demo entry execution controlled re-enablement key active ---
# _demo_entry_execution_key is defined above with the 34 helper block.
# --- end 4B.4.3.6.6.34 ---
