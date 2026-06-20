from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_execution_candidate_gate import (
    READY_DECISION,
    SOURCE_30F_REQUIRED_DECISION,
    build_paper_sandbox_dry_run_execution_candidate_gate_snapshot,
)


def fake_30f_ready() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30F",
        "decision": "PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_transition_plan": True,
        "approved_for_paper_sandbox_dry_run_execution_plan": True,
        "approved_for_order_path_simulation_envelope": True,
        "approved_for_operator_final_go_no_go_checklist": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "order_path_simulation_envelope": {
            "runtime_envelope": "sandbox_only",
            "execution_mode": "dry_run",
            "market_type": "spot_demo",
            "base_url": "https://demo-api.binance.com",
            "auto_trade_on_signal": False,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
            "order_notional_usd": 25.0,
            "order_notional_cap_usd": 25.0,
            "max_open_orders": 1,
        },
    }


def test_missing_30f_source_blocks_candidate_gate() -> None:
    payload = build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(Settings(), {})
    assert payload["decision"] == SOURCE_30F_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_execution_candidate_gate"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_ready_source_builds_single_simulated_intent_without_exchange_submit() -> None:
    payload = build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(Settings(), fake_30f_ready())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_execution_candidate_gate"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution_candidate"] is True
    assert payload["approved_for_single_simulated_paper_intent"] is True
    assert payload["approved_for_no_exchange_submit_verification"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["single_simulated_paper_intent"]["intent_count"] == 1
    assert payload["single_simulated_paper_intent"]["submitted_to_exchange"] is False
    assert payload["no_exchange_submit"]["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False


def test_live_real_runtime_envelope_blocks_candidate_gate() -> None:
    source = fake_30f_ready()
    source["order_path_simulation_envelope"] = {
        **source["order_path_simulation_envelope"],  # type: ignore[index]
        "execution_mode": "live_real",
        "live_trading_armed": True,
    }
    payload = build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(Settings(), source)
    assert payload["decision"] != READY_DECISION
    assert payload["dry_run_only_runtime_envelope_verified"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution_candidate_gate"] is False
    assert payload["approved_for_live_real"] is False


def test_paper_candidate_still_blocks_even_with_ready_plan_shape() -> None:
    source = fake_30f_ready()
    source["approved_for_paper_candidate"] = True
    payload = build_paper_sandbox_dry_run_execution_candidate_gate_snapshot(Settings(), source)
    assert payload["approved_for_paper_sandbox_dry_run_execution_candidate_gate"] is False
    assert payload["paper_candidate_still_blocked_verified"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
