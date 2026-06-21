from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_canary_reconciliation import (
    INTENT_REQUIRED_DECISION,
    READY_DECISION,
    SOURCE_30Q_REQUIRED_DECISION,
    build_paper_sandbox_canary_reconciliation_snapshot,
)


def source_30q() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30Q",
        "decision": "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL",
        "approved_for_first_paper_sandbox_canary_submit_gate": True,
        "source_30p_submit_arm_verified": True,
        "operator_canary_approval_verified": True,
        "sandbox_submit_readiness_verified": True,
        "single_sandbox_order_intent_built": True,
        "canary_order_intent_written": True,
        "exchange_submit_path_guarded": True,
        "submit_still_blocked": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def intent() -> dict[str, object]:
    return {
        "intent_id": "canary-intent-test",
        "contract_version": "4B.4.3.6.6.30Q",
        "event_type": "first_paper_sandbox_canary_single_order_intent_submit_guarded_no_exchange_submit",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 10.0,
        "quantity": 0.004,
        "submit_path_guarded": True,
        "submit_to_exchange": False,
        "submitted_to_exchange": False,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def test_ready_reconciles_mismatch_zero() -> None:
    payload = build_paper_sandbox_canary_reconciliation_snapshot(Settings(), source_30q(), intent())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_canary_reconciliation"] is True
    assert payload["mismatch_count"] == 0
    assert payload["submit_remained_guarded_verified"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_missing_30q_source() -> None:
    payload = build_paper_sandbox_canary_reconciliation_snapshot(Settings(), {}, intent())
    assert payload["decision"] == SOURCE_30Q_REQUIRED_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_bad_intent_submit_attempt() -> None:
    bad = intent()
    bad["network_submit_attempted"] = True
    payload = build_paper_sandbox_canary_reconciliation_snapshot(Settings(), source_30q(), bad)
    assert payload["decision"] == INTENT_REQUIRED_DECISION
    assert payload["submit_remained_guarded_verified"] is False
    assert payload["exchange_submit_performed"] is False


def test_mismatch_nonzero_blocks_ready() -> None:
    settings = Settings(paper_sandbox_canary_reconciliation_expected_fill_count=1)
    payload = build_paper_sandbox_canary_reconciliation_snapshot(settings, source_30q(), intent())
    assert payload["decision"] != READY_DECISION
    assert payload["mismatch_count"] == 1
