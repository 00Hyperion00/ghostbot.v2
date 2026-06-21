from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.live_real_final_operator_approval import (
    APPROVAL_TOKEN,
    CONTRACT_VERSION,
    OPERATOR_APPROVAL_REQUIRED_DECISION,
    READY_DECISION,
    build_live_real_final_operator_approval_snapshot,
    evaluate_operator_approval,
    evaluate_source_30v_preflight,
    latest_valid_30v_preflight_report,
    write_report_bundle,
)


def source_30v() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30V",
        "decision": "LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER",
        "approved_for_live_real_preflight_gate": True,
        "approved_for_live_real_readiness_candidate": True,
        "api_env_capability_audit_verified": True,
        "account_capability_audit_verified": True,
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


def test_contract_version_is_30w() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.30W"


def test_source_30v_preflight_requires_ready_decision_and_zero_activity() -> None:
    status = evaluate_source_30v_preflight(source_30v())
    assert status.ok is True
    bad = source_30v()
    bad["approved_for_exchange_submit"] = True
    bad_status = evaluate_source_30v_preflight(bad)
    assert bad_status.ok is False
    assert "SOURCE_30V_EXCHANGE_SUBMIT_UNEXPECTEDLY_ENABLED_OR_PERFORMED" in bad_status.reason_codes


def test_default_requires_operator_approval_without_enabling_live_real() -> None:
    payload = build_live_real_final_operator_approval_snapshot(Settings(), source_30v())
    assert payload["decision"] == OPERATOR_APPROVAL_REQUIRED_DECISION
    assert payload["source_30v_live_real_preflight_verified"] is True
    assert payload["approved_for_live_real_final_operator_approval"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["live_real_order_performed"] is False


def test_explicit_operator_approval_ready_but_submit_remains_blocked() -> None:
    payload = build_live_real_final_operator_approval_snapshot(
        Settings(),
        source_30v(),
        operator_id="operator-30w",
        approval_token=APPROVAL_TOKEN,
        issue_final_approval=True,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_live_real_final_operator_approval"] is True
    assert payload["approved_for_30x_live_real_micro_canary_candidate"] is True
    assert payload["live_real_submit_blocked_until_30x"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_count"] == 0
    assert payload["network_submit_count"] == 0
    assert payload["live_real_order_submitted"] is False


def test_operator_approval_rejects_wrong_token() -> None:
    status = evaluate_operator_approval(
        Settings(),
        operator_id="operator-30w",
        approval_token="WRONG",
        issue_final_approval=True,
    )
    assert status.ok is False
    assert "LIVE_REAL_FINAL_OPERATOR_APPROVAL_TOKEN_MISMATCH" in status.reason_codes


def test_latest_valid_30v_and_report_bundle(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    invalid = dict(source_30v())
    invalid["decision"] = "NOT_READY"
    (reports_dir / "4B436630V_live_real_preflight_gate_20260621T000000Z_ready.json").write_text(__import__("json").dumps(invalid), encoding="utf-8")
    valid_path = reports_dir / "4B436630V_live_real_preflight_gate_20260621T000001Z_ready.json"
    valid_path.write_text(__import__("json").dumps(source_30v()), encoding="utf-8")
    found_path, payload = latest_valid_30v_preflight_report(reports_dir)
    assert found_path == valid_path
    assert payload["contract_version"] == "4B.4.3.6.6.30V"
    ready = build_live_real_final_operator_approval_snapshot(
        Settings(),
        payload,
        source_report_path=str(found_path),
        operator_id="operator-30w",
        approval_token=APPROVAL_TOKEN,
        issue_final_approval=True,
    )
    json_path, md_path = write_report_bundle(ready, reports_dir)
    assert json_path.exists()
    assert md_path.exists()
    assert "LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY" in md_path.read_text(encoding="utf-8")
