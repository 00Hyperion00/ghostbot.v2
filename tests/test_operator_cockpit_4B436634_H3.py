from __future__ import annotations

import sys
import types

# The patch verification fixture contains only cockpit files. Provide minimal
# import-time stubs for sibling modules; the real project modules are used at runtime.
config_stub = types.ModuleType("tradebot.config")
config_stub.Settings = type("Settings", (), {})
sys.modules.setdefault("tradebot.config", config_stub)
engine_stub = types.ModuleType("tradebot.engine")
engine_stub.TradeBotEngine = type("TradeBotEngine", (), {})
sys.modules.setdefault("tradebot.engine", engine_stub)
persistence_stub = types.ModuleType("tradebot.persistence")
persistence_stub.SQLiteStore = type("SQLiteStore", (), {})
sys.modules.setdefault("tradebot.persistence", persistence_stub)
hardening_stub = types.ModuleType("tradebot.production_hardening")
hardening_stub.RuntimeLockHandle = type("RuntimeLockHandle", (), {})
hardening_stub.acquire_runtime_lock = lambda *args, **kwargs: None
hardening_stub.release_runtime_lock = lambda *args, **kwargs: None
sys.modules.setdefault("tradebot.production_hardening", hardening_stub)

from tradebot.cockpit.orchestrator import (
    _build_force_buy_execution_binding,
    _post_entry_protective_exit_record,
    build_demo_entry_execution_gate_snapshot,
)


class Settings:
    symbol = "ETHUSDT"
    market_type = "spot_demo"
    execution_mode = "live_demo"
    base_url = "https://demo-api.binance.com"


def _ready_guard() -> dict:
    return {"entry_actions_enabled": True, "force_buy_disabled": False, "entry_block_until_reconciled": False, "risk_badge": "GREEN", "entry_guard_release_authorized": True}


def _cache_ready() -> dict:
    return {"runtime_snapshot_override_active": True, "stale_engine_balance_invalidated": True, "entry_guard_release_stabilized_after_safe_apply": True, "no_mismatch_from_verified_fresh_source": True}


def test_missing_force_buy_result_without_position_fails_closed_and_does_not_consume_authorization() -> None:
    binding = _build_force_buy_execution_binding(result=None, status_after={"position_snapshot": {"present": False}}, demo_gate={"status": "DEMO_ENTRY_ENABLEMENT_READY"}, operator_id="operator-local")
    assert binding["order_result_bound"] is False
    assert binding["order_accepted"] is False
    assert binding["authorization_should_be_consumed"] is False
    assert binding["no_fill_no_protection_fail_closed"] is True
    assert "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in binding["reason_codes"]


def test_order_result_with_identifier_and_protected_position_is_accepted_and_protected() -> None:
    binding = _build_force_buy_execution_binding(
        result={"orderId": 123, "status": "FILLED", "executedQty": "0.004", "cummulativeQuoteQty": "10"},
        status_after={"position_snapshot": {"present": True, "qty": 0.004, "protective_exit": {"present": True, "stop_loss_order_id": "sl-1"}}},
        demo_gate={"status": "DEMO_ENTRY_ENABLEMENT_READY"},
        operator_id="operator-local",
    )
    assert binding["order_result_bound"] is True
    assert binding["order_accepted"] is True
    assert binding["order_executed"] is True
    assert binding["authorization_should_be_consumed"] is True
    assert binding["post_entry_protective_exit_verified"] is True
    assert binding["no_fill_no_protection_fail_closed"] is False


def test_gate_becomes_fail_closed_after_unprotected_execution_attempt() -> None:
    state = {
        "latest_dry_run": {"dry_run_passed": True, "filter_review": {"filters_ok": True}},
        "latest_filter_review": {"filters_ok": True},
        "latest_intent": {"intent_recorded": True},
        "demo_trade_authorization": {"authorized": True, "expires_at_ms": 9999999999999999999, "consumed": False},
        "latest_force_buy_execution": {"order_result_bound": False, "order_accepted": False, "no_fill_no_protection_fail_closed": True},
    }
    gate = build_demo_entry_execution_gate_snapshot(settings=Settings(), status={"symbol": "ETHUSDT", "risk_badge": "GREEN"}, entry_guard=_ready_guard(), source_gate={"no_mismatch_from_verified_fresh_source": True}, cache_reconciliation=_cache_ready(), state=state)
    assert gate["demo_trade_enablement_ready"] is False
    assert gate["no_fill_no_protection_fail_closed"] is True
    assert gate["status"] == "DEMO_ENTRY_EXECUTION_FAIL_CLOSED_NO_PROTECTION"


def test_post_entry_record_reports_missing_position_after_execution() -> None:
    record = _post_entry_protective_exit_record(status={"position_snapshot": {"present": False}}, operator_id="operator-local", latest_execution={"force_buy_invoked": True})
    assert record["protective_exit_verified"] is False
    assert "POST_ENTRY_POSITION_NOT_PRESENT" in record["reason_codes"]
    assert "NO_FILL_NO_PROTECTION_FAIL_CLOSED" in record["reason_codes"]
