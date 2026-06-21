from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.live_real_micro_canary_gate import (
    APPROVAL_TOKEN,
    CONTRACT_VERSION,
    OPERATOR_APPROVAL_REQUIRED_DECISION,
    READY_DECISION,
    build_first_live_real_micro_canary_snapshot,
    evaluate_order_request,
    evaluate_source_30w_final_approval,
    latest_valid_30w_final_operator_approval_report,
    write_report_bundle,
)


def source_30w() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30W",
        "decision": "LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_FINAL_APPROVAL_CAPTURED_SUBMIT_BLOCKED_UNTIL_30X_NO_LIVE_REAL_ORDER",
        "approved_for_live_real_final_operator_approval": True,
        "approved_for_30x_live_real_micro_canary_candidate": True,
        "final_operator_approval_verified": True,
        "live_real_submit_blocked_until_30x": True,
        "hard_live_submit_block_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_order_verified": True,
        "order_action_count": 0,
        "exchange_submit_count": 0,
        "network_submit_count": 0,
        "total_notional_usd": 0.0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "live_real_order_performed": False,
        "live_real_order_submitted": False,
        "live_real_network_submit_attempted": False,
    }


def test_contract_version_is_30x() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.30X"


def test_source_30w_requires_final_approval_and_zero_prior_activity() -> None:
    status = evaluate_source_30w_final_approval(source_30w())
    assert status.ok is True
    bad = source_30w()
    bad["approved_for_exchange_submit"] = True
    bad_status = evaluate_source_30w_final_approval(bad)
    assert bad_status.ok is False
    assert "SOURCE_30W_UNEXPECTED_SUBMIT_OR_ORDER_ACTIVITY" in bad_status.reason_codes


def test_default_requires_micro_canary_operator_approval() -> None:
    payload = build_first_live_real_micro_canary_snapshot(Settings(), source_30w())
    assert payload["decision"] == OPERATOR_APPROVAL_REQUIRED_DECISION
    assert payload["source_30w_final_operator_approval_verified"] is True
    assert payload["approved_for_first_live_real_micro_canary_gate"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["network_submit_attempted"] is False
    assert payload["live_real_order_performed"] is False


def test_explicit_micro_canary_ready_builds_request_without_automated_network_submit(tmp_path: Path) -> None:
    payload = build_first_live_real_micro_canary_snapshot(
        Settings(),
        source_30w(),
        operator_id="operator-30x",
        approval_token=APPROVAL_TOKEN,
        issue_micro_canary_approval=True,
        symbol="ETHUSDT",
        side="BUY",
        quantity="0.002",
        mark_price="2500",
        write_submit_request=True,
        reports_dir=tmp_path,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_first_live_real_micro_canary_gate"] is True
    assert payload["approved_for_exchange_submit"] is True
    assert payload["approved_for_live_real"] is True
    assert payload["submit_request_built"] is True
    assert payload["submit_request_count"] == 1
    assert payload["total_notional_usd"] == 5.0
    assert payload["exchange_submit_performed"] is False
    assert payload["network_submit_attempted"] is False
    assert payload["live_real_order_performed"] is False
    assert Path(str(payload["submit_request_path"])).exists()


def test_order_request_rejects_notional_above_cap() -> None:
    status = evaluate_order_request(Settings(), quantity="1", mark_price="2500")
    assert status.ok is False
    assert "MICRO_CANARY_NOTIONAL_OUTSIDE_MIN_MAX_CAPS" in status.reason_codes


def test_latest_valid_30w_report_and_bundle_round_trip(tmp_path: Path) -> None:
    ready = source_30w()
    source_path = tmp_path / "4B436630W_live_real_final_operator_approval_20260621T000000Z_ready.json"
    source_path.write_text(__import__("json").dumps(ready), encoding="utf-8")
    selected, payload = latest_valid_30w_final_operator_approval_report(tmp_path)
    assert selected == source_path
    assert payload["contract_version"] == "4B.4.3.6.6.30W"
    built = build_first_live_real_micro_canary_snapshot(
        Settings(), payload, operator_id="operator-30x", approval_token=APPROVAL_TOKEN, issue_micro_canary_approval=True
    )
    json_path, md_path = write_report_bundle(built, tmp_path)
    assert json_path.exists()
    assert md_path.exists()
