from __future__ import annotations

import hmac
import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import HTTPException

OPERATOR_COCKPIT_SECURITY_GATE_VERSION = "4B.4.3.6.6.33C"
OPERATOR_COCKPIT_SECURITY_GATE_ENABLED = True
AUTH_ENV_KEYS = ("TRADEBOT_API_AUTH_TOKEN", "TRADEBOT_COCKPIT_AUTH_TOKEN")
DEFAULT_AUTH_HEADER = "X-TradeBot-Auth"
OPERATOR_ID_HEADER = "X-TradeBot-Operator"
CONFIRM_HEADER = "X-TradeBot-Confirm"
READ_ONLY_HEALTH_PATHS = frozenset({"/health", "/api/cockpit/health"})
PUBLIC_PATHS = frozenset({"/", "/favicon.ico"})
PUBLIC_PATH_PREFIXES = ("/static/",)

DANGER_ACTION_CONFIRMATIONS: dict[str, str] = {
    "trade.force_buy": "CONFIRM_FORCE_BUY",
    "trade.force_sell": "CONFIRM_FORCE_SELL",
    "trade.cancel_pending": "CONFIRM_CANCEL_PENDING",
    "risk.reset": "CONFIRM_RISK_RESET",
    "risk.safe_mode.toggle": "CONFIRM_SAFE_MODE_TOGGLE",
    "runtime_lock.clear_stale": "CONFIRM_CLEAR_STALE_RUNTIME_LOCK",
    "risk_reconciliation.acknowledge": "CONFIRM_ACKNOWLEDGE_POSITION_NOT_TRACKED",
    "risk_reconciliation.clear_acknowledgement": "CONFIRM_CLEAR_RECONCILIATION_ACKNOWLEDGEMENT",
    "risk_reconciliation.confirm_balance_snapshot": "CONFIRM_BALANCE_SNAPSHOT_REVIEWED",
    "risk_reconciliation.resolve_dust_safe": "CONFIRM_RESOLVE_DUST_SAFE_BASE_BALANCE",
    "risk_reconciliation.adopt_position_candidate": "CONFIRM_ADOPT_TRACKED_POSITION_CANDIDATE",
    "risk_reconciliation.apply_tracked_position_candidate_review": "CONFIRM_APPLY_TRACKED_POSITION_CANDIDATE_REVIEW",
    "risk_reconciliation.apply_dust_safe_clear": "CONFIRM_APPLY_DUST_SAFE_CLEAR",
    "risk_reconciliation.clear_manual_decision": "CONFIRM_CLEAR_RECONCILIATION_DECISION",
    "runtime_lock.resolve_owner_mismatch": "CONFIRM_RESOLVE_RUNTIME_LOCK_OWNER_MISMATCH",
    "engine_position_recovery.create_plan": "CONFIRM_CREATE_ENGINE_POSITION_RECOVERY_PLAN",
    "engine_position_recovery.confirm_plan": "CONFIRM_CONFIRM_ENGINE_POSITION_RECOVERY_PLAN",
    "engine_position_recovery.verify_completion": "CONFIRM_VERIFY_ENGINE_POSITION_RECOVERY_COMPLETE",
    "engine_position_recovery.clear_plan": "CONFIRM_CLEAR_ENGINE_POSITION_RECOVERY_PLAN",
    "recovery_plan_apply.create_from_reviewed_candidate": "CONFIRM_CREATE_RECOVERY_PLAN_FROM_REVIEWED_CANDIDATE",
    "recovery_plan_apply.confirm_manual_external_recovery": "CONFIRM_CONFIRM_MANUAL_EXTERNAL_RECOVERY_PLAN",
    "recovery_plan_apply.verify_no_mismatch": "CONFIRM_VERIFY_RECOVERY_NO_MISMATCH",
    "recovery_plan_apply.clear": "CONFIRM_CLEAR_RECOVERY_PLAN_APPLY",
    "external_recovery_evidence.capture": "CONFIRM_CAPTURE_EXTERNAL_RECOVERY_EVIDENCE",
    "external_recovery_evidence.capture_post_recovery_snapshot": "CONFIRM_CAPTURE_POST_RECOVERY_BALANCE_SNAPSHOT",
    "external_recovery_evidence.no_mismatch_preflight": "CONFIRM_RUN_EXTERNAL_RECOVERY_NO_MISMATCH_PREFLIGHT",
    "external_recovery_evidence.verify_no_mismatch_safe_apply": "CONFIRM_VERIFY_RECOVERY_NO_MISMATCH_WITH_EVIDENCE",
    "external_recovery_evidence.clear": "CONFIRM_CLEAR_EXTERNAL_RECOVERY_EVIDENCE",
    "exchange_environment.verify_consistency": "CONFIRM_VERIFY_EXCHANGE_ENVIRONMENT_CONSISTENCY",
    "exchange_environment.capture_fresh_balance": "CONFIRM_CAPTURE_FRESH_EXCHANGE_BALANCE_SOURCE",
    "exchange_environment.clear": "CONFIRM_CLEAR_EXCHANGE_ENVIRONMENT_SOURCE_GATE",
    "demo_entry.dry_run": "CONFIRM_DEMO_ENTRY_DRY_RUN",
    "demo_entry.verify_filters": "CONFIRM_VERIFY_DEMO_ENTRY_FILTERS",
    "demo_entry.record_intent": "CONFIRM_RECORD_DEMO_ENTRY_INTENT",
    "demo_entry.authorize_demo_only_entry": "CONFIRM_AUTHORIZE_DEMO_ONLY_ENTRY",
    "demo_entry.verify_post_entry_protective_exit": "CONFIRM_VERIFY_POST_ENTRY_PROTECTIVE_EXIT",
    "demo_entry.clear": "CONFIRM_CLEAR_DEMO_ENTRY_EXECUTION_GATE",
}
MUTATING_ACTIONS = frozenset({
    "engine.start",
    "engine.stop",
    "engine.restart",
    *DANGER_ACTION_CONFIRMATIONS.keys(),
})


@dataclass(frozen=True, slots=True)
class CockpitAuthPolicy:
    auth_required: bool
    auth_configured: bool
    fail_closed_no_token: bool
    explicitly_enabled: bool
    elevated_runtime: bool
    token_source: str
    auth_header: str
    operator_header: str = OPERATOR_ID_HEADER
    confirm_header: str = CONFIRM_HEADER
    security_gate_version: str = OPERATOR_COCKPIT_SECURITY_GATE_VERSION
    reason_codes: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("token_source", None)
        payload["token_configured"] = self.auth_configured
        payload["token_source_present"] = bool(self.token_source)
        payload["danger_action_count"] = len(DANGER_ACTION_CONFIRMATIONS)
        payload["danger_actions"] = [
            {"action": action, "confirmation": confirmation}
            for action, confirmation in sorted(DANGER_ACTION_CONFIRMATIONS.items())
        ]
        payload["read_only_health_exception_paths"] = sorted(READ_ONLY_HEALTH_PATHS)
        payload["static_assets_public"] = True
        return payload


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _stripped(value: Any) -> str:
    return str(value or "").strip()


def resolve_auth_header(settings: Any) -> str:
    configured = _stripped(getattr(settings, "api_auth_header", ""))
    return configured or DEFAULT_AUTH_HEADER


def resolve_auth_token(settings: Any) -> tuple[str, str]:
    configured = _stripped(getattr(settings, "api_auth_token", ""))
    if configured:
        return configured, "settings.api_auth_token"
    for key in AUTH_ENV_KEYS:
        value = _stripped(os.getenv(key, ""))
        if value:
            return value, f"env.{key}"
    return "", ""


def build_auth_policy(settings: Any) -> CockpitAuthPolicy:
    token, source = resolve_auth_token(settings)
    explicitly_enabled = _truthy(getattr(settings, "api_auth_enabled", False))
    execution_mode = _stripped(getattr(settings, "execution_mode", "dry_run")).lower()
    market_type = _stripped(getattr(settings, "market_type", "")).lower()
    elevated_runtime = bool(
        execution_mode in {"live_demo", "live_real"}
        or market_type in {"spot_testnet", "spot_mainnet"}
        or _truthy(getattr(settings, "auto_trade_on_signal", False))
        or _truthy(getattr(settings, "live_trading_armed", False))
        or _truthy(getattr(settings, "live_real_double_confirm", False))
    )
    auth_required = bool(explicitly_enabled or elevated_runtime or token)
    fail_closed_no_token = bool(auth_required and not token)
    reasons: list[str] = []
    if explicitly_enabled:
        reasons.append("API_AUTH_EXPLICITLY_ENABLED")
    if elevated_runtime:
        reasons.append("ELEVATED_RUNTIME_REQUIRES_AUTH")
    if token:
        reasons.append("AUTH_TOKEN_CONFIGURED")
    if fail_closed_no_token:
        reasons.append("AUTH_REQUIRED_BUT_NO_TOKEN_CONFIGURED")
    if not auth_required:
        reasons.append("LOCAL_DRY_RUN_AUTH_BYPASS")
    return CockpitAuthPolicy(
        auth_required=auth_required,
        auth_configured=bool(token),
        fail_closed_no_token=fail_closed_no_token,
        explicitly_enabled=explicitly_enabled,
        elevated_runtime=elevated_runtime,
        token_source=source,
        auth_header=resolve_auth_header(settings),
        reason_codes=tuple(reasons),
    )


def is_public_http_path(path: str) -> bool:
    clean = str(path or "")
    if clean in READ_ONLY_HEALTH_PATHS or clean in PUBLIC_PATHS:
        return True
    return any(clean.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)


def compare_token(expected: str, supplied: str | None) -> bool:
    return bool(expected) and hmac.compare_digest(expected, _stripped(supplied))


def authenticate_http_request(settings: Any, *, path: str, supplied_token: str | None, operator_id: str | None) -> dict[str, Any]:
    policy = build_auth_policy(settings)
    if is_public_http_path(path):
        return {
            "ok": True,
            "authenticated": False,
            "public_path": True,
            "operator_id": normalize_operator_id(operator_id),
            "policy": policy.to_public_dict(),
        }
    if not str(path or "").startswith("/api/"):
        return {
            "ok": True,
            "authenticated": False,
            "public_path": True,
            "operator_id": normalize_operator_id(operator_id),
            "policy": policy.to_public_dict(),
        }
    expected, _source = resolve_auth_token(settings)
    if policy.fail_closed_no_token:
        raise HTTPException(
            status_code=503,
            detail={
                "ok": False,
                "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
                "reason_code": "COCKPIT_AUTH_REQUIRED_NO_TOKEN_CONFIGURED",
                "message": "Cockpit API auth is required for this runtime, but no token is configured.",
                "auth_header": policy.auth_header,
                "health_exception": sorted(READ_ONLY_HEALTH_PATHS),
            },
        )
    if policy.auth_required and not compare_token(expected, supplied_token):
        raise HTTPException(
            status_code=401,
            detail={
                "ok": False,
                "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
                "reason_code": "COCKPIT_AUTH_TOKEN_INVALID_OR_MISSING",
                "message": "Supply the configured cockpit API token using the auth header.",
                "auth_header": policy.auth_header,
            },
        )
    return {
        "ok": True,
        "authenticated": bool(policy.auth_required),
        "public_path": False,
        "operator_id": normalize_operator_id(operator_id),
        "policy": policy.to_public_dict(),
    }


def authenticate_websocket(settings: Any, *, supplied_token: str | None, operator_id: str | None) -> dict[str, Any]:
    policy = build_auth_policy(settings)
    expected, _source = resolve_auth_token(settings)
    if policy.fail_closed_no_token:
        return {"ok": False, "reason_code": "COCKPIT_AUTH_REQUIRED_NO_TOKEN_CONFIGURED", "policy": policy.to_public_dict()}
    if policy.auth_required and not compare_token(expected, supplied_token):
        return {"ok": False, "reason_code": "COCKPIT_AUTH_TOKEN_INVALID_OR_MISSING", "policy": policy.to_public_dict()}
    return {"ok": True, "operator_id": normalize_operator_id(operator_id), "policy": policy.to_public_dict()}


def normalize_operator_id(value: Any) -> str | None:
    clean = _stripped(value)
    if not clean or clean in {"-", "unknown", "UNKNOWN", "null", "None"}:
        return None
    return clean[:96]


def require_operator_identity(operator_id: str | None, *, action: str) -> str:
    normalized = normalize_operator_id(operator_id)
    if normalized:
        return normalized
    raise HTTPException(
        status_code=428,
        detail={
            "ok": False,
            "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
            "reason_code": "COCKPIT_OPERATOR_IDENTITY_REQUIRED",
            "message": "Supply operator identity using X-TradeBot-Operator before mutating cockpit state.",
            "operator_header": OPERATOR_ID_HEADER,
            "action": action,
        },
    )


def confirmation_required_exception(*, action: str, expected: str) -> HTTPException:
    return HTTPException(
        status_code=412,
        detail={
            "ok": False,
            "security_gate_version": OPERATOR_COCKPIT_SECURITY_GATE_VERSION,
            "reason_code": "COCKPIT_TYPED_CONFIRMATION_REQUIRED",
            "action": action,
            "confirmation_header": CONFIRM_HEADER,
            "expected_confirmation": expected,
        },
    )


def build_security_snapshot(settings: Any) -> dict[str, Any]:
    policy = build_auth_policy(settings)
    payload = policy.to_public_dict()
    payload.update(
        {
            "security_gate_enabled": True,
            "operator_identity_header": OPERATOR_ID_HEADER,
            "confirmation_header": CONFIRM_HEADER,
            "mutating_actions_require_operator_id": True,
            "danger_actions_require_typed_confirmation": True,
            "read_only_health_exception_enabled": True,
            "health_paths": sorted(READ_ONLY_HEALTH_PATHS),
        }
    )
    return payload


def fetch_recent_operator_actions(store: Any, *, limit: int = 80) -> list[dict[str, Any]]:
    conn = getattr(store, "_conn", None)
    lock = getattr(store, "_lock", None)
    if conn is None:
        return []
    sql = "SELECT ts, action, actor, confirmation, outcome, data FROM operator_actions ORDER BY id DESC LIMIT ?"
    try:
        if lock is None:
            rows = conn.execute(sql, (int(limit),)).fetchall()
        else:
            with lock:
                rows = conn.execute(sql, (int(limit),)).fetchall()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            data = json.loads(row[5] or "{}")
        except Exception:
            data = {}
        out.append(
            {
                "ts": row[0],
                "action": row[1],
                "actor": row[2],
                "confirmation": bool(row[3]),
                "outcome": row[4],
                "data": data,
            }
        )
    return out
