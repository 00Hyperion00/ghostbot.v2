from __future__ import annotations

import hmac
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

API_SECURITY_CONTRACT_VERSION = "4B.4.3.6.6.29B"
API_OPERATOR_SECURITY_HARDENING_ENABLED = True
TOKEN_TTL_ENFORCED_WHEN_CONFIGURED = True
LIVE_REAL_ARM_TTL_ENFORCED = True
OPERATOR_AUDIT_BASELINE_ENABLED = True
LOCAL_ONLY_BINDING_VERIFICATION_ENABLED = True

DESTRUCTIVE_CONFIRMATIONS: dict[tuple[str, str], str] = {
    ("POST", "/start"): "CONFIRM_START",
    ("POST", "/force-buy"): "CONFIRM_FORCE_BUY",
    ("POST", "/force-sell"): "CONFIRM_FORCE_SELL",
    ("POST", "/cancel-pending"): "CONFIRM_CANCEL_PENDING",
    ("POST", "/risk-reset"): "CONFIRM_RISK_RESET",
    ("POST", "/safe-mode/toggle"): "CONFIRM_SAFE_MODE_TOGGLE",
    ("POST", "/ai/train"): "CONFIRM_AI_TRAIN",
    ("POST", "/ai/reload"): "CONFIRM_AI_RELOAD",
}


@dataclass(frozen=True, slots=True)
class OperatorSecurityDecision:
    ok: bool
    reason_code: str
    method: str
    path: str
    destructive_action: bool
    operator_id: str
    auth_checked: bool
    token_ttl_checked: bool
    typed_confirmation_checked: bool
    live_real_arm_ttl_checked: bool
    local_only_checked: bool

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contract_version"] = API_SECURITY_CONTRACT_VERSION
        return payload


def _now_ms() -> int:
    return int(time.time() * 1000)


def _get_setting(settings: Any, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _int_setting(settings: Any, name: str, default: int) -> int:
    try:
        return int(_get_setting(settings, name, default) or 0)
    except (TypeError, ValueError):
        return int(default)


def _resolve_token(settings: Any) -> str:
    configured = str(_get_setting(settings, "api_auth_token", "") or "").strip()
    env_name = str(_get_setting(settings, "api_auth_env_var", "TRADEBOT_API_TOKEN") or "TRADEBOT_API_TOKEN").strip()
    env_token = str(os.environ.get(env_name, "") or "").strip() if env_name else ""
    return configured or env_token


def _resolve_token_issued_at_ms(settings: Any) -> int:
    configured = _int_setting(settings, "api_auth_token_issued_at_ms", 0)
    if configured > 0:
        return configured
    env_name = str(_get_setting(settings, "api_auth_token_issued_at_env_var", "TRADEBOT_API_TOKEN_ISSUED_AT_MS") or "TRADEBOT_API_TOKEN_ISSUED_AT_MS").strip()
    if not env_name:
        return 0
    try:
        return int(os.environ.get(env_name, "0") or "0")
    except ValueError:
        return 0


def _is_live_real(settings: Any) -> bool:
    return str(_get_setting(settings, "execution_mode", "") or "").strip().lower() == "live_real"


def _is_loopback_client(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    return normalized in {"127.0.0.1", "::1", "localhost", "testclient"} or normalized.startswith("127.")


def _operator_id(settings: Any, request: Request) -> str:
    header = str(_get_setting(settings, "api_operator_id_header", "X-TradeBot-Operator") or "X-TradeBot-Operator")
    supplied = str(request.headers.get(header, "") or "").strip()
    if supplied:
        return supplied[:128]
    client = getattr(request, "client", None)
    return f"client:{getattr(client, 'host', 'unknown')}"


def _log(logger: Any, level: str, code: str, message: str, data: dict[str, Any]) -> None:
    fn = getattr(logger, level, None) if logger is not None else None
    if callable(fn):
        try:
            fn(code, message, data)
        except Exception:
            pass


def _audit_operator_action(
    logger: Any,
    settings: Any,
    *,
    outcome: str,
    reason_code: str,
    method: str,
    path: str,
    operator_id: str,
    destructive: bool,
    confirmation: str | None = None,
    status_code: int | None = None,
) -> None:
    if not _truthy(_get_setting(settings, "operator_audit_enabled", True)):
        return
    level = "info" if outcome == "ALLOWED" else "warn"
    code = "OPERATOR_API_ACTION_ALLOWED" if outcome == "ALLOWED" else "OPERATOR_API_ACTION_BLOCKED"
    _log(
        logger,
        level,
        code,
        "Operator API action audit event",
        {
            "contract_version": API_SECURITY_CONTRACT_VERSION,
            "outcome": outcome,
            "reason_code": reason_code,
            "method": method,
            "path": path,
            "operator_id": operator_id,
            "destructive_action": bool(destructive),
            "confirmation": confirmation or "",
            "status_code": status_code,
            "runtime_overlay_activation_performed": False,
            "paper_live_order_enablement_present": False,
            "training_reload_performed_by_guard": False,
        },
    )


def _block(
    logger: Any,
    settings: Any,
    *,
    status_code: int,
    reason_code: str,
    message: str,
    method: str,
    path: str,
    operator_id: str,
    destructive: bool,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    _audit_operator_action(
        logger,
        settings,
        outcome="BLOCKED",
        reason_code=reason_code,
        method=method,
        path=path,
        operator_id=operator_id,
        destructive=destructive,
        status_code=status_code,
    )
    payload: dict[str, Any] = {
        "ok": False,
        "contract_version": API_SECURITY_CONTRACT_VERSION,
        "reason_code": reason_code,
        "message": message,
        "operator_id": operator_id,
        "method": method,
        "path": path,
    }
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)


def _token_ttl_response_if_blocked(settings: Any, *, now_ms: int) -> tuple[str, dict[str, Any]] | None:
    ttl_sec = _int_setting(settings, "api_auth_token_ttl_sec", 0)
    if ttl_sec <= 0:
        return None
    issued_at_ms = _resolve_token_issued_at_ms(settings)
    if issued_at_ms <= 0:
        return "API_AUTH_TOKEN_ISSUED_AT_MISSING", {
            "token_ttl_sec": ttl_sec,
            "token_issued_at_ms": issued_at_ms,
        }
    expires_at_ms = issued_at_ms + ttl_sec * 1000
    if now_ms > expires_at_ms:
        return "API_AUTH_TOKEN_EXPIRED", {
            "token_ttl_sec": ttl_sec,
            "token_issued_at_ms": issued_at_ms,
            "token_expires_at_ms": expires_at_ms,
            "now_ms": now_ms,
        }
    return None


def _live_arm_response_if_blocked(settings: Any, request: Request, *, now_ms: int) -> tuple[str, dict[str, Any]] | None:
    if not _is_live_real(settings):
        return None
    ttl_sec = _int_setting(settings, "live_real_arm_ttl_sec", 0)
    if ttl_sec <= 0:
        return "LIVE_REAL_ARM_TTL_NOT_CONFIGURED", {"live_real_arm_ttl_sec": ttl_sec}
    armed_at_ms = _int_setting(settings, "live_real_armed_at_ms", 0)
    expires_at_ms = _int_setting(settings, "live_real_arm_expires_at_ms", 0)
    if armed_at_ms <= 0 and expires_at_ms <= 0:
        return "LIVE_REAL_ARM_NOT_PRESENT", {"live_real_arm_ttl_sec": ttl_sec}
    if expires_at_ms <= 0 and armed_at_ms > 0:
        expires_at_ms = armed_at_ms + ttl_sec * 1000
    if now_ms > expires_at_ms:
        return "LIVE_REAL_ARM_EXPIRED", {
            "live_real_armed_at_ms": armed_at_ms,
            "live_real_arm_expires_at_ms": expires_at_ms,
            "now_ms": now_ms,
        }
    header_name = str(_get_setting(settings, "live_real_arm_confirmation_header", "X-TradeBot-Live-Arm") or "X-TradeBot-Live-Arm")
    expected = str(_get_setting(settings, "live_real_start_confirmation", "CONFIRM_LIVE_REAL_START") or "CONFIRM_LIVE_REAL_START")
    supplied = str(request.headers.get(header_name, "") or "").strip()
    if not hmac.compare_digest(supplied, expected):
        return "LIVE_REAL_ARM_CONFIRMATION_REQUIRED", {
            "expected_confirmation": expected,
            "confirmation_header": header_name,
        }
    return None


def install_api_security(app: FastAPI, settings: Any, *, logger: Any = None) -> FastAPI:
    if getattr(app.state, "tradebot_api_security_installed", False):
        return app
    app.state.tradebot_api_security_installed = True
    app.state.tradebot_api_security_contract_version = API_SECURITY_CONTRACT_VERSION

    @app.middleware("http")
    async def tradebot_api_security_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        method = request.method.upper()
        path = request.url.path.rstrip("/") or "/"
        action_key = (method, path)
        destructive = action_key in DESTRUCTIVE_CONFIRMATIONS
        operator_id = _operator_id(settings, request)
        now_ms = _now_ms()

        local_only_required = _truthy(_get_setting(settings, "api_local_only_required", True))
        client_host = str(getattr(getattr(request, "client", None), "host", "") or "")
        if local_only_required and not _is_loopback_client(client_host):
            return _block(
                logger,
                settings,
                status_code=403,
                reason_code="API_LOCAL_ONLY_REQUIRED",
                message="API requests are restricted to loopback clients",
                method=method,
                path=path,
                operator_id=operator_id,
                destructive=destructive,
                extra={"client_host": client_host},
            )

        auth_enabled = _truthy(_get_setting(settings, "api_auth_enabled", False))
        if auth_enabled:
            header_name = str(_get_setting(settings, "api_auth_header", "X-TradeBot-Auth") or "X-TradeBot-Auth")
            expected = _resolve_token(settings)
            if not expected:
                return _block(
                    logger,
                    settings,
                    status_code=503,
                    reason_code="API_AUTH_TOKEN_MISSING",
                    message="API auth is enabled but no token is configured",
                    method=method,
                    path=path,
                    operator_id=operator_id,
                    destructive=destructive,
                )
            ttl_block = _token_ttl_response_if_blocked(settings, now_ms=now_ms)
            if ttl_block is not None:
                reason_code, extra = ttl_block
                return _block(
                    logger,
                    settings,
                    status_code=401,
                    reason_code=reason_code,
                    message="API token TTL validation failed",
                    method=method,
                    path=path,
                    operator_id=operator_id,
                    destructive=destructive,
                    extra=extra,
                )
            supplied = str(request.headers.get(header_name, "") or "").strip()
            if not hmac.compare_digest(supplied, expected):
                return _block(
                    logger,
                    settings,
                    status_code=401,
                    reason_code="API_AUTH_REQUIRED",
                    message="Valid API token is required",
                    method=method,
                    path=path,
                    operator_id=operator_id,
                    destructive=destructive,
                )

        confirmation_checked = False
        confirmation_required = _truthy(_get_setting(settings, "destructive_action_confirmation_required", False))
        if destructive and confirmation_required:
            confirmation_checked = True
            confirm_header = str(_get_setting(settings, "destructive_action_confirmation_header", "X-TradeBot-Confirm") or "X-TradeBot-Confirm")
            expected_confirm = DESTRUCTIVE_CONFIRMATIONS[action_key]
            supplied_confirm = str(request.headers.get(confirm_header, "") or "").strip()
            if not hmac.compare_digest(supplied_confirm, expected_confirm):
                return _block(
                    logger,
                    settings,
                    status_code=412,
                    reason_code="DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED",
                    message="Typed destructive action confirmation is required",
                    method=method,
                    path=path,
                    operator_id=operator_id,
                    destructive=destructive,
                    extra={"expected_confirmation": expected_confirm, "confirmation_header": confirm_header},
                )

        if method == "POST" and path == "/start":
            live_arm_block = _live_arm_response_if_blocked(settings, request, now_ms=now_ms)
            if live_arm_block is not None:
                reason_code, extra = live_arm_block
                return _block(
                    logger,
                    settings,
                    status_code=412,
                    reason_code=reason_code,
                    message="Live-real start requires a fresh typed live arm confirmation",
                    method=method,
                    path=path,
                    operator_id=operator_id,
                    destructive=destructive,
                    extra=extra,
                )

        response = await call_next(request)
        response.headers["X-TradeBot-Api-Security-Contract"] = API_SECURITY_CONTRACT_VERSION
        if destructive:
            _audit_operator_action(
                logger,
                settings,
                outcome="ALLOWED",
                reason_code="OPERATOR_API_ACTION_ALLOWED",
                method=method,
                path=path,
                operator_id=operator_id,
                destructive=destructive,
                confirmation=DESTRUCTIVE_CONFIRMATIONS.get(action_key) if confirmation_checked else None,
                status_code=int(getattr(response, "status_code", 0) or 0),
            )
        return response

    return app


def build_operator_security_snapshot(settings: Any) -> dict[str, Any]:
    return {
        "contract_version": API_SECURITY_CONTRACT_VERSION,
        "api_operator_security_hardening_enabled": True,
        "api_auth_enabled": bool(_get_setting(settings, "api_auth_enabled", False)),
        "token_ttl_sec": _int_setting(settings, "api_auth_token_ttl_sec", 0),
        "token_ttl_enforced_when_configured": True,
        "destructive_action_confirmation_required": bool(_get_setting(settings, "destructive_action_confirmation_required", False)),
        "destructive_actions": {f"{method} {path}": phrase for (method, path), phrase in sorted(DESTRUCTIVE_CONFIRMATIONS.items())},
        "local_only_required": bool(_get_setting(settings, "api_local_only_required", True)),
        "operator_audit_enabled": bool(_get_setting(settings, "operator_audit_enabled", True)),
        "live_real_arm_ttl_sec": _int_setting(settings, "live_real_arm_ttl_sec", 0),
        "live_real_arm_ttl_enforced": True,
        "runtime_overlay_activation_performed": False,
        "paper_live_order_enablement_present": False,
        "training_reload_performed_by_guard": False,
    }


__all__ = [
    "API_SECURITY_CONTRACT_VERSION",
    "API_OPERATOR_SECURITY_HARDENING_ENABLED",
    "DESTRUCTIVE_CONFIRMATIONS",
    "LIVE_REAL_ARM_TTL_ENFORCED",
    "OPERATOR_AUDIT_BASELINE_ENABLED",
    "OperatorSecurityDecision",
    "build_operator_security_snapshot",
    "install_api_security",
]
