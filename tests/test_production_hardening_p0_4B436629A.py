from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tradebot.api_security import install_api_security
from tradebot.config import Settings
from tradebot.persistence import SQLiteStore
from tradebot.production_hardening import (
    acquire_runtime_lock,
    build_production_hardening_snapshot,
    canonical_evidence_commit_decision,
    evaluate_promotion_gate,
    release_runtime_lock,
)


def test_strict_config_rejects_unknown_yaml_key(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbol: ETHUSDT\nmax_daily_los_pct: 99\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown Settings yaml key"):
        Settings.from_yaml(cfg)


def test_api_auth_and_typed_confirmation_guard() -> None:
    app = FastAPI()
    settings = SimpleNamespace(
        api_auth_enabled=True,
        api_auth_token="secret-token",
        api_auth_header="X-TradeBot-Auth",
        api_auth_env_var="TRADEBOT_API_TOKEN",
        destructive_action_confirmation_required=True,
        destructive_action_confirmation_header="X-TradeBot-Confirm",
    )
    install_api_security(app, settings)

    @app.post("/force-buy")
    async def force_buy() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert client.post("/force-buy").status_code == 401
    assert client.post("/force-buy", headers={"X-TradeBot-Auth": "secret-token"}).status_code == 412
    ok = client.post(
        "/force-buy",
        headers={"X-TradeBot-Auth": "secret-token", "X-TradeBot-Confirm": "CONFIRM_FORCE_BUY"},
    )
    assert ok.status_code == 200
    assert ok.json() == {"ok": True}


def test_sqlite_audit_baseline_integrity_and_schema(tmp_path: Path) -> None:
    store = SQLiteStore(str(tmp_path / "tradebot.db"))
    result = store.integrity_check()
    assert result["ok"] is True
    assert result["schema_version"] >= 1
    with store._lock:  # noqa: SLF001 - test verifies migration table exists
        row = store._conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()  # noqa: SLF001
    assert row is not None


def test_runtime_lock_and_promotion_gate_blocking(tmp_path: Path) -> None:
    lock = acquire_runtime_lock(tmp_path / "runtime.lock", identity="pytest")
    with pytest.raises(RuntimeError, match="RUNTIME_LOCK_ALREADY_HELD"):
        acquire_runtime_lock(tmp_path / "runtime.lock", identity="second")
    release_runtime_lock(lock)
    gate = evaluate_promotion_gate(
        target="runtime_overlay_activation",
        hypothesis_payload={"matured_count": 30, "win_rate_pct": 80.0},
    )
    assert gate["allowed"] is False
    assert "HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS" in gate["reason_codes"]
    assert gate["approved_for_runtime_overlay_activation"] is False


def test_hardening_snapshot_and_report_policy() -> None:
    settings = Settings()
    snapshot = build_production_hardening_snapshot(settings)
    assert snapshot["contract_version"] == "4B.4.3.6.6.29A"
    assert snapshot["promotion_gate_isolation"]["production_readiness_not_inferred_from_hypothesis_performance"] is True
    assert snapshot["mutations"]["trading_action_performed"] is False
    assert canonical_evidence_commit_decision("tools/_patch_backup_x/file.py")["canonical_evidence_commit_allowed"] is False


def test_fee_slippage_baseline_defaults_are_non_zero() -> None:
    source = Path("src/tradebot/training/labeling.py").read_text(encoding="utf-8")
    assert "entry_fee_bps: float = 0.0" not in source
    assert "entry_fee_bps: float = 10.0" in source
    assert "min_profit_bps: float = 24.0" in source
