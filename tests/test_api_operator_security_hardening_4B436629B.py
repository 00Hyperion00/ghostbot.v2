from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tradebot.api_security import (
    API_SECURITY_CONTRACT_VERSION,
    build_operator_security_snapshot,
    install_api_security,
)


@dataclass
class DummySettings:
    api_auth_enabled: bool = False
    api_auth_token: str = ""
    api_auth_header: str = "X-TradeBot-Auth"
    api_auth_env_var: str = "TRADEBOT_API_TOKEN"
    api_auth_token_ttl_sec: int = 900
    api_auth_token_issued_at_ms: int = 0
    api_auth_token_issued_at_env_var: str = "TRADEBOT_API_TOKEN_ISSUED_AT_MS"
    api_operator_id_header: str = "X-TradeBot-Operator"
    api_local_only_required: bool = False
    destructive_action_confirmation_required: bool = False
    destructive_action_confirmation_header: str = "X-TradeBot-Confirm"
    operator_audit_enabled: bool = True
    execution_mode: str = "dry_run"
    live_real_arm_ttl_sec: int = 900
    live_real_armed_at_ms: int = 0
    live_real_arm_expires_at_ms: int = 0
    live_real_arm_confirmation_header: str = "X-TradeBot-Live-Arm"
    live_real_start_confirmation: str = "CONFIRM_LIVE_REAL_START"


@dataclass
class DummyLogger:
    events: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)

    def info(self, code: str, message: str, data: dict[str, Any]) -> None:
        self.events.append(("info", code, data))

    def warn(self, code: str, message: str, data: dict[str, Any]) -> None:
        self.events.append(("warn", code, data))


def _client(settings: DummySettings, logger: DummyLogger | None = None) -> TestClient:
    app = FastAPI()
    install_api_security(app, settings, logger=logger)

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/force-buy")
    async def force_buy() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/start")
    async def start() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_destructive_confirmation_blocks_and_audits() -> None:
    logger = DummyLogger()
    settings = DummySettings(destructive_action_confirmation_required=True)
    client = _client(settings, logger)

    blocked = client.post("/force-buy", headers={"X-TradeBot-Operator": "operator-a"})
    assert blocked.status_code == 412
    assert blocked.json()["reason_code"] == "DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED"

    allowed = client.post(
        "/force-buy",
        headers={
            "X-TradeBot-Operator": "operator-a",
            "X-TradeBot-Confirm": "CONFIRM_FORCE_BUY",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["X-TradeBot-Api-Security-Contract"] == API_SECURITY_CONTRACT_VERSION
    codes = [event[1] for event in logger.events]
    assert "OPERATOR_API_ACTION_BLOCKED" in codes
    assert "OPERATOR_API_ACTION_ALLOWED" in codes


def test_token_ttl_blocks_expired_token() -> None:
    issued_at = int((time() - 10) * 1000)
    settings = DummySettings(
        api_auth_enabled=True,
        api_auth_token="secret",
        api_auth_token_ttl_sec=1,
        api_auth_token_issued_at_ms=issued_at,
    )
    client = _client(settings)

    response = client.get("/health", headers={"X-TradeBot-Auth": "secret"})
    assert response.status_code == 401
    assert response.json()["reason_code"] == "API_AUTH_TOKEN_EXPIRED"


def test_live_real_start_requires_fresh_typed_live_arm() -> None:
    now_ms = int(time() * 1000)
    settings = DummySettings(
        execution_mode="live_real",
        destructive_action_confirmation_required=True,
        live_real_armed_at_ms=now_ms,
        live_real_arm_ttl_sec=900,
    )
    client = _client(settings)

    missing_live_arm = client.post("/start", headers={"X-TradeBot-Confirm": "CONFIRM_START"})
    assert missing_live_arm.status_code == 412
    assert missing_live_arm.json()["reason_code"] == "LIVE_REAL_ARM_CONFIRMATION_REQUIRED"

    allowed = client.post(
        "/start",
        headers={
            "X-TradeBot-Confirm": "CONFIRM_START",
            "X-TradeBot-Live-Arm": "CONFIRM_LIVE_REAL_START",
        },
    )
    assert allowed.status_code == 200


def test_operator_security_snapshot_exposes_29b_controls() -> None:
    snapshot = build_operator_security_snapshot(DummySettings())
    assert snapshot["contract_version"] == API_SECURITY_CONTRACT_VERSION
    assert snapshot["token_ttl_enforced_when_configured"] is True
    assert snapshot["live_real_arm_ttl_enforced"] is True
    assert snapshot["operator_audit_enabled"] is True
    assert snapshot["paper_live_order_enablement_present"] is False
