from __future__ import annotations

from tradebot.config import Settings
from tradebot.live_real_micro_canary_reconciliation import (
    MISMATCH_DECISION,
    READY_DECISION,
    build_live_real_micro_canary_reconciliation_snapshot,
    build_manual_execution_evidence,
    evaluate_source_30x_submit_request,
)


def source_30x() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30X",
        "decision": "FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT",
        "approved_for_first_live_real_micro_canary_gate": True,
        "approved_for_manual_runtime_handoff": True,
        "approved_for_exchange_submit": True,
        "approved_for_live_real": True,
        "automated_network_submit_disabled_verified": True,
        "submit_request_built": True,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
    }


def request_30x() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30X",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 0.002,
        "mark_price_reference": 2500.0,
        "notional_usd_reference": 5.0,
        "client_order_id": "tbv2-30x-test",
    }


def test_real_binance_min_notional_quantity_adjustment_can_reconcile() -> None:
    status = evaluate_source_30x_submit_request(source_30x(), request_30x())
    evidence = build_manual_execution_evidence(
        status,
        operator_id="operator-30y",
        exchange_order_id="8114595899",
        filled_quantity="0.0029",
        avg_fill_price="1713.36",
        account_position_delta_qty="0.0029",
        ledger_event_id="MANUAL_30Y_ETHUSDT_8114595899_20260622T002601",
        ledger_filled_quantity="0.0029",
        ledger_notional_usd="4.968744",
        allow_min_notional_quantity_adjustment=True,
        quantity_adjustment_reason="manual Binance minimum notional quantity adjustment from 30X request",
    )
    payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source_30x(), request_30x(), evidence)
    assert payload["decision"] == READY_DECISION
    assert payload["mismatch_count"] == 0
    assert payload["fill_reconciliation_verified"] is True
    assert payload["reconciliation"]["manual_min_notional_quantity_adjustment_accepted"] is True
    assert "MANUAL_MIN_NOTIONAL_QUANTITY_ADJUSTMENT_ACCEPTED" in payload["reconciliation"]["reason_codes"]
    assert payload["patch_network_submit_attempted"] is False
    assert payload["approved_for_additional_exchange_submit"] is False


def test_quantity_adjustment_without_explicit_approval_remains_mismatch() -> None:
    status = evaluate_source_30x_submit_request(source_30x(), request_30x())
    evidence = build_manual_execution_evidence(
        status,
        operator_id="operator-30y",
        exchange_order_id="8114595899",
        filled_quantity="0.0029",
        avg_fill_price="1713.36",
        account_position_delta_qty="0.0029",
        ledger_event_id="MANUAL_30Y_ETHUSDT_8114595899_20260622T002601",
        ledger_filled_quantity="0.0029",
        ledger_notional_usd="4.968744",
    )
    payload = build_live_real_micro_canary_reconciliation_snapshot(Settings(), source_30x(), request_30x(), evidence)
    assert payload["decision"] == MISMATCH_DECISION
    assert payload["mismatch_count"] == 1
    assert "QUANTITY_MISMATCH" in payload["reason_codes"]
