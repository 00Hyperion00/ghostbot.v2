from __future__ import annotations

from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.paper_mode_runtime_guardrail import (
    CAPS_NOT_READY_DECISION,
    KILL_SWITCH_REQUIRED_DECISION,
    READY_DECISION,
    SOURCE_30R_REQUIRED_DECISION,
    build_paper_mode_runtime_guardrail_snapshot,
)


def source_30r() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30R",
        "decision": "PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_canary_reconciliation": True,
        "source_30q_canary_gate_verified": True,
        "canary_order_intent_consumed": True,
        "intent_fill_account_reconciled": True,
        "submit_remained_guarded_verified": True,
        "mismatch_zero_verified": True,
        "mismatch_count": 0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_ready_guarded_loop_caps_kill_switch() -> None:
    payload = build_paper_mode_runtime_guardrail_snapshot(Settings(), source_30r())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_mode_runtime_guardrail"] is True
    assert payload["source_30r_reconciliation_verified"] is True
    assert payload["guarded_runtime_loop_verified"] is True
    assert payload["strict_caps_verified"] is True
    assert payload["kill_switch_verified"] is True
    assert payload["loop_tick_count"] == 3
    assert payload["order_action_count"] == 0
    assert payload["exchange_submit_count"] == 0
    assert payload["network_submit_count"] == 0
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_missing_30r_source() -> None:
    payload = build_paper_mode_runtime_guardrail_snapshot(Settings(), {})
    assert payload["decision"] == SOURCE_30R_REQUIRED_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_source_mismatch_nonzero() -> None:
    bad = source_30r()
    bad["mismatch_count"] = 1
    bad["mismatch_zero_verified"] = False
    payload = build_paper_mode_runtime_guardrail_snapshot(Settings(), bad)
    assert payload["decision"] == SOURCE_30R_REQUIRED_DECISION
    assert payload["source_30r_reconciliation_verified"] is False


def test_blocks_cap_violation() -> None:
    settings = SimpleNamespace(
        paper_mode_runtime_guardrail_max_ticks=6,
        paper_mode_runtime_guardrail_tick_cap=5,
        paper_mode_runtime_guardrail_order_action_cap=0,
        paper_mode_runtime_guardrail_exchange_submit_cap=0,
        paper_mode_runtime_guardrail_network_submit_cap=0,
        paper_mode_runtime_guardrail_max_notional_usd=0.0,
        paper_mode_runtime_guardrail_runtime_seconds_cap=30,
        paper_mode_runtime_guardrail_kill_switch_enabled=True,
    )
    payload = build_paper_mode_runtime_guardrail_snapshot(settings, source_30r())
    assert payload["decision"] == "PAPER_MODE_RUNTIME_GUARDRAIL_LOOP_NOT_READY_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL"
    assert payload["approved_for_paper_mode_runtime_guardrail"] is False


def test_blocks_kill_switch_disabled() -> None:
    settings = SimpleNamespace(
        paper_mode_runtime_guardrail_max_ticks=3,
        paper_mode_runtime_guardrail_tick_cap=5,
        paper_mode_runtime_guardrail_order_action_cap=0,
        paper_mode_runtime_guardrail_exchange_submit_cap=0,
        paper_mode_runtime_guardrail_network_submit_cap=0,
        paper_mode_runtime_guardrail_max_notional_usd=0.0,
        paper_mode_runtime_guardrail_runtime_seconds_cap=30,
        paper_mode_runtime_guardrail_kill_switch_enabled=False,
    )
    payload = build_paper_mode_runtime_guardrail_snapshot(settings, source_30r())
    assert payload["decision"] == KILL_SWITCH_REQUIRED_DECISION
    assert payload["kill_switch_verified"] is False
