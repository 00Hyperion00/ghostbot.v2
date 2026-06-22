from __future__ import annotations

import json
from pathlib import Path

from tradebot.post_live_micro_canary_risk_review import (
    ADDITIONAL_ORDER_BLOCK_DECISION,
    FEE_EVIDENCE_REQUIRED_DECISION,
    READY_DECISION,
    SOURCE_REQUIRED_DECISION,
    build_from_latest_30y_h1_reconciliation,
    build_post_live_micro_canary_risk_review_snapshot,
    evaluate_source_30y_h1_reconciliation,
    write_report_bundle,
)


def source_30y_h1() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30Y-H1",
        "decision": "LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED",
        "source_30x_submit_request_verified": True,
        "mismatch_zero_verified": True,
        "mismatch_count": 0,
        "emergency_stop_armed_verified": True,
        "further_live_real_submit_blocked": True,
        "approved_for_additional_exchange_submit": False,
        "patch_network_submit_attempted": False,
        "patch_exchange_submit_performed": False,
        "execution_evidence": {
            "exchange_order_id": "8114595899",
            "symbol": "ETHUSDT",
            "side": "BUY",
            "filled_quantity": 0.0029,
            "avg_fill_price": 1713.36,
            "fill_notional_usd": 4.968744,
            "fee_amount": 0.0000029,
            "fee_asset": "ETH",
        },
        "reconciliation": {
            "ledger_event_id": "MANUAL_30Y_ETHUSDT_8114595899_20260622T002601",
            "ledger_filled_quantity": 0.0029,
            "ledger_notional_usd": 4.968744,
            "manual_min_notional_quantity_adjustment_accepted": True,
        },
    }


def test_ready_review_consumes_30y_h1_and_keeps_no_additional_order() -> None:
    payload = build_post_live_micro_canary_risk_review_snapshot(
        source_30y_h1(),
        fee_amount=0.0000029,
        fee_asset="ETH",
        review_mark_price=1713.36,
        reference_price=1713.36,
        emergency_stop_armed=True,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["source_30y_h1_reconciliation_verified"] is True
    assert payload["fee_evidence_verified"] is True
    assert payload["pnl_evidence_verified"] is True
    assert payload["slippage_evidence_verified"] is True
    assert payload["emergency_stop_continuity_verified"] is True
    assert payload["additional_live_order_count"] == 0
    assert payload["approved_for_additional_live_order"] is False
    assert payload["patch_network_submit_attempted"] is False


def test_fee_evidence_required_when_fee_missing() -> None:
    source = source_30y_h1()
    execution = dict(source["execution_evidence"])  # type: ignore[index]
    execution.pop("fee_amount")
    execution.pop("fee_asset")
    source["execution_evidence"] = execution
    payload = build_post_live_micro_canary_risk_review_snapshot(source, review_mark_price=1713.36, reference_price=1713.36, emergency_stop_armed=True)
    assert payload["decision"] == FEE_EVIDENCE_REQUIRED_DECISION
    assert payload["fee_evidence_verified"] is False


def test_invalid_source_remains_not_ready() -> None:
    source = source_30y_h1()
    source["decision"] = "BAD"
    payload = build_post_live_micro_canary_risk_review_snapshot(source, fee_amount=0.1, fee_asset="USDT", emergency_stop_armed=True)
    assert payload["decision"] == SOURCE_REQUIRED_DECISION
    status = evaluate_source_30y_h1_reconciliation(source)
    assert status.ok is False


def test_additional_live_order_blocks_ready() -> None:
    payload = build_post_live_micro_canary_risk_review_snapshot(
        source_30y_h1(),
        fee_amount=0.0000029,
        fee_asset="ETH",
        review_mark_price=1713.36,
        reference_price=1713.36,
        emergency_stop_armed=True,
        additional_live_order_count=1,
    )
    assert payload["decision"] == ADDITIONAL_ORDER_BLOCK_DECISION
    assert "ADDITIONAL_LIVE_ORDER_DETECTED" in payload["reason_codes"]


def test_latest_source_selection_and_bundle_round_trip(tmp_path: Path) -> None:
    src = source_30y_h1()
    source_path = tmp_path / "4B436630Y_live_real_micro_canary_reconciliation_20260622T010000Z_ready.json"
    source_path.write_text(json.dumps(src), encoding="utf-8")
    payload = build_from_latest_30y_h1_reconciliation(
        tmp_path,
        fee_amount=0.0000029,
        fee_asset="ETH",
        review_mark_price=1713.36,
        reference_price=1713.36,
        emergency_stop_armed=True,
    )
    assert payload["decision"] == READY_DECISION
    json_path, md_path = write_report_bundle(payload, tmp_path)
    assert json_path.exists()
    assert md_path.exists()
