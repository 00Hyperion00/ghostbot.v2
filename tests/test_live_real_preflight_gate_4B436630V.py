from __future__ import annotations

from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.live_real_preflight_gate import (
    CAPABILITY_AUDIT_NOT_READY_DECISION,
    HARD_BLOCK_NOT_READY_DECISION,
    READY_DECISION,
    SOURCE_30U_READY_DECISION,
    SOURCE_30U_REQUIRED_DECISION,
    build_live_real_preflight_gate_snapshot,
)


def source_30u() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30U",
        "decision": SOURCE_30U_READY_DECISION,
        "approved_for_paper_promotion_review": True,
        "approved_for_paper_runtime_promotion_candidate": True,
        "risk_acceptance_gates_verified": True,
        "promotion_readiness_review_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_verified": True,
        "soak_cycle_count": 5,
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
    }


def test_ready_preflight_from_valid_30u_without_secret_persistence() -> None:
    payload = build_live_real_preflight_gate_snapshot(Settings(), source_30u(), env={})
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_live_real_preflight_gate"] is True
    assert payload["approved_for_live_real_readiness_candidate"] is True
    assert payload["source_30u_promotion_review_verified"] is True
    assert payload["api_env_capability_audit_verified"] is True
    assert payload["account_capability_audit_verified"] is True
    assert payload["hard_live_submit_block_verified"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["network_submit_attempted"] is False
    assert payload["live_real_order_performed"] is False
    assert payload["capability_audit"]["api_key_redacted"] == "absent"
    assert payload["capability_audit"]["no_secret_material_persisted"] is True


def test_blocks_missing_source_30u() -> None:
    payload = build_live_real_preflight_gate_snapshot(Settings(), {}, env={})
    assert payload["decision"] == SOURCE_30U_REQUIRED_DECISION
    assert payload["approved_for_live_real_preflight_gate"] is False
    assert payload["source_30u_promotion_review_verified"] is False


def test_blocks_source_exchange_or_live_flags() -> None:
    source = source_30u()
    source["approved_for_exchange_submit"] = True
    source["approved_for_live_real"] = True
    source["exchange_submit_performed"] = True
    source["network_submit_attempted"] = True
    payload = build_live_real_preflight_gate_snapshot(Settings(), source, env={})
    assert payload["decision"] == SOURCE_30U_REQUIRED_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["live_real_order_performed"] is False


def test_api_key_presence_required_blocks_without_keys() -> None:
    settings = SimpleNamespace(
        live_real_preflight_capability_audit_required=True,
        live_real_preflight_api_env_audit_required=True,
        live_real_preflight_account_capability_audit_required=True,
        live_real_preflight_api_key_presence_required=True,
        live_real_preflight_account_capability_mode="offline_redacted_audit",
        live_real_preflight_hard_submit_block_required=True,
        live_real_preflight_no_live_order_required=True,
        live_real_preflight_exchange_submit_cap=0,
        live_real_preflight_network_submit_cap=0,
        live_real_preflight_order_action_cap=0,
    )
    payload = build_live_real_preflight_gate_snapshot(settings, source_30u(), env={})
    assert payload["decision"] == CAPABILITY_AUDIT_NOT_READY_DECISION
    assert payload["api_env_capability_audit_verified"] is False


def test_api_key_presence_required_passes_with_redacted_keys() -> None:
    settings = SimpleNamespace(
        live_real_preflight_capability_audit_required=True,
        live_real_preflight_api_env_audit_required=True,
        live_real_preflight_account_capability_audit_required=True,
        live_real_preflight_api_key_presence_required=True,
        live_real_preflight_account_capability_mode="offline_redacted_audit",
        live_real_preflight_hard_submit_block_required=True,
        live_real_preflight_no_live_order_required=True,
        live_real_preflight_exchange_submit_cap=0,
        live_real_preflight_network_submit_cap=0,
        live_real_preflight_order_action_cap=0,
    )
    payload = build_live_real_preflight_gate_snapshot(
        settings,
        source_30u(),
        env={"BINANCE_API_KEY": "abc123", "BINANCE_API_SECRET": "def456"},
    )
    assert payload["decision"] == READY_DECISION
    assert payload["capability_audit"]["api_key_redacted"] == "present_redacted"
    assert payload["capability_audit"]["api_secret_redacted"] == "present_redacted"


def test_blocks_if_hard_submit_block_disabled() -> None:
    settings = SimpleNamespace(
        live_real_preflight_capability_audit_required=True,
        live_real_preflight_api_env_audit_required=True,
        live_real_preflight_account_capability_audit_required=True,
        live_real_preflight_api_key_presence_required=False,
        live_real_preflight_account_capability_mode="offline_redacted_audit",
        live_real_preflight_hard_submit_block_required=False,
        live_real_preflight_no_live_order_required=True,
        live_real_preflight_exchange_submit_cap=0,
        live_real_preflight_network_submit_cap=0,
        live_real_preflight_order_action_cap=0,
    )
    payload = build_live_real_preflight_gate_snapshot(settings, source_30u(), env={})
    assert payload["decision"] == HARD_BLOCK_NOT_READY_DECISION
    assert payload["hard_live_submit_block_verified"] is False
