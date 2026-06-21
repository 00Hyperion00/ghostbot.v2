from __future__ import annotations

from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.paper_soak_evidence_window import (
    KILL_SWITCH_REQUIRED_DECISION,
    SOAK_NOT_READY_DECISION,
    READY_DECISION,
    SOURCE_30S_REQUIRED_DECISION,
    build_paper_soak_evidence_window_snapshot,
)


def source_30s() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30S",
        "decision": "PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_mode_runtime_guardrail": True,
        "source_30r_reconciliation_verified": True,
        "guarded_runtime_loop_verified": True,
        "strict_caps_verified": True,
        "kill_switch_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_verified": True,
        "loop_tick_count": 3,
        "order_action_count": 0,
        "exchange_submit_count": 0,
        "network_submit_count": 0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_ready_multi_cycle_soak_caps_kill_switch() -> None:
    payload = build_paper_soak_evidence_window_snapshot(Settings(), source_30s())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_soak_evidence_window"] is True
    assert payload["source_30s_guardrail_verified"] is True
    assert payload["multi_cycle_soak_verified"] is True
    assert payload["cap_continuity_verified"] is True
    assert payload["kill_switch_continuity_verified"] is True
    assert payload["soak_cycle_count"] == 5
    assert payload["minimum_soak_cycles_required"] == 3
    assert payload["order_action_count"] == 0
    assert payload["exchange_submit_count"] == 0
    assert payload["network_submit_count"] == 0
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_missing_source_30s() -> None:
    payload = build_paper_soak_evidence_window_snapshot(Settings(), {})
    assert payload["decision"] == SOURCE_30S_REQUIRED_DECISION
    assert payload["approved_for_paper_soak_evidence_window"] is False
    assert payload["source_30s_guardrail_verified"] is False


def test_blocks_requested_cycles_over_cap() -> None:
    settings = SimpleNamespace(
        paper_soak_evidence_window_cycle_count=11,
        paper_soak_evidence_window_min_cycles_required=3,
        paper_soak_evidence_window_cycle_cap=10,
        paper_soak_evidence_window_kill_switch_enabled=True,
    )
    payload = build_paper_soak_evidence_window_snapshot(settings, source_30s())
    assert payload["decision"] == SOAK_NOT_READY_DECISION
    assert payload["approved_for_paper_soak_evidence_window"] is False


def test_blocks_kill_switch_disabled() -> None:
    settings = SimpleNamespace(
        paper_soak_evidence_window_cycle_count=5,
        paper_soak_evidence_window_min_cycles_required=3,
        paper_soak_evidence_window_cycle_cap=10,
        paper_soak_evidence_window_kill_switch_required=True,
        paper_soak_evidence_window_kill_switch_enabled=False,
    )
    payload = build_paper_soak_evidence_window_snapshot(settings, source_30s())
    assert payload["decision"] == KILL_SWITCH_REQUIRED_DECISION
    assert payload["kill_switch_continuity_verified"] is False


def test_blocks_source_exchange_or_live_flags() -> None:
    source = source_30s()
    source["approved_for_exchange_submit"] = True
    source["approved_for_live_real"] = True
    payload = build_paper_soak_evidence_window_snapshot(Settings(), source)
    assert payload["decision"] == SOURCE_30S_REQUIRED_DECISION
    assert payload["approved_for_paper_soak_evidence_window"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
