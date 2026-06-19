from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

API_SECURITY_CONTRACT_VERSION = "4B.4.3.6.6.29A"

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


def _get_setting(settings: Any, name: str, default: Any) -> Any:
    return getattr(settings, name, default)


def _resolve_token(settings: Any) -> str:
    configured = str(_get_setting(settings, "api_auth_token", "") or "").strip()
    env_name = str(_get_setting(settings, "api_auth_env_var", "TRADEBOT_API_TOKEN") or "TRADEBOT_API_TOKEN").strip()
    env_token = str(os.environ.get(env_name, "") or "").strip() if env_name else ""
    return configured or env_token


def _log(logger: Any, level: str, code: str, message: str, data: dict[str, Any]) -> None:
    fn = getattr(logger, level, None) if logger is not None else None
    if callable(fn):
        try:
            fn(code, message, data)
        except Exception:
            pass


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

        auth_enabled = bool(_get_setting(settings, "api_auth_enabled", False))
        if auth_enabled:
            header_name = str(_get_setting(settings, "api_auth_header", "X-TradeBot-Auth") or "X-TradeBot-Auth")
            expected = _resolve_token(settings)
            if not expected:
                _log(logger, "warn", "API_AUTH_TOKEN_MISSING", "API auth enabled but no token is configured", {"path": path, "method": method})
                return JSONResponse(status_code=503, content={
                    "ok": False,
                    "contract_version": API_SECURITY_CONTRACT_VERSION,
                    "reason_code": "API_AUTH_TOKEN_MISSING",
                    "message": "API auth is enabled but no token is configured",
                })
            supplied = str(request.headers.get(header_name, "") or "").strip()
            if supplied != expected:
                _log(logger, "warn", "API_AUTH_REQUIRED", "API request blocked by auth guard", {"path": path, "method": method})
                return JSONResponse(status_code=401, content={
                    "ok": False,
                    "contract_version": API_SECURITY_CONTRACT_VERSION,
                    "reason_code": "API_AUTH_REQUIRED",
                    "message": "Valid API token is required",
                })

        confirmation_required = bool(_get_setting(settings, "destructive_action_confirmation_required", False))
        if destructive and confirmation_required:
            confirm_header = str(_get_setting(settings, "destructive_action_confirmation_header", "X-TradeBot-Confirm") or "X-TradeBot-Confirm")
            expected_confirm = DESTRUCTIVE_CONFIRMATIONS[action_key]
            supplied_confirm = str(request.headers.get(confirm_header, "") or "").strip()
            if supplied_confirm != expected_confirm:
                _log(logger, "warn", "DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED", "Destructive API action blocked by confirmation guard", {"path": path, "method": method, "expectedConfirmation": expected_confirm})
                return JSONResponse(status_code=412, content={
                    "ok": False,
                    "contract_version": API_SECURITY_CONTRACT_VERSION,
                    "reason_code": "DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED",
                    "message": "Typed destructive action confirmation is required",
                    "expected_confirmation": expected_confirm,
                })

        response = await call_next(request)
        response.headers["X-TradeBot-Api-Security-Contract"] = API_SECURITY_CONTRACT_VERSION
        return response

    return app
