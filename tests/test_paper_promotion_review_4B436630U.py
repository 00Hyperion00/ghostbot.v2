from __future__ import annotations

from types import SimpleNamespace

from tradebot.config import Settings
from tradebot.paper_promotion_review import (
    READY_DECISION,
    RISK_GATES_NOT_READY_DECISION,
    SOURCE_30T_READY_DECISION,
    SOURCE_30T_REQUIRED_DECISION,
    build_paper_promotion_review_snapshot,
)


def source_30t() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30T",
        "decision": SOURCE_30T_READY_DECISION,
        "approved_for_paper_soak_evidence_window": True,
        "source_30s_guardrail_verified": True,
        "multi_cycle_soak_verified": True,
        "cap_continuity_verified": True,
        "kill_switch_continuity_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_verified": True,
        "soak_cycle_count": 5,
        "minimum_soak_cycles_required": 3,
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


def test_ready_promotion_review_from_valid_30t() -> None:
    payload = build_paper_promotion_review_snapshot(Settings(), source_30t())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_promotion_review"] is True
    assert payload["approved_for_paper_runtime_promotion_candidate"] is True
    assert payload["source_30t_soak_verified"] is True
    assert payload["risk_acceptance_gates_verified"] is True
    assert payload["promotion_readiness_review_verified"] is True
    assert payload["order_action_count"] == 0
    assert payload["exchange_submit_count"] == 0
    assert payload["network_submit_count"] == 0
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_blocks_missing_source_30t() -> None:
    payload = build_paper_promotion_review_snapshot(Settings(), {})
    assert payload["decision"] == SOURCE_30T_REQUIRED_DECISION
    assert payload["approved_for_paper_promotion_review"] is False
    assert payload["source_30t_soak_verified"] is False


def test_blocks_low_soak_cycles() -> None:
    source = source_30t()
    source["soak_cycle_count"] = 2
    source["minimum_soak_cycles_required"] = 3
    payload = build_paper_promotion_review_snapshot(Settings(), source)
    assert payload["decision"] == SOURCE_30T_REQUIRED_DECISION
    assert payload["approved_for_paper_promotion_review"] is False


def test_blocks_disabled_promotion_review_gate() -> None:
    settings = SimpleNamespace(
        paper_promotion_review_enabled=False,
        paper_promotion_review_risk_acceptance_required=True,
        paper_promotion_review_consume_30t_required=True,
        paper_promotion_review_min_soak_cycles_required=3,
        paper_promotion_review_zero_action_counts_required=True,
        paper_promotion_review_no_exchange_submit_required=True,
        paper_promotion_review_no_live_real_required=True,
        paper_promotion_review_cap_continuity_required=True,
        paper_promotion_review_kill_switch_required=True,
        paper_promotion_review_max_total_notional_usd=0.0,
    )
    payload = build_paper_promotion_review_snapshot(settings, source_30t())
    assert payload["decision"] == RISK_GATES_NOT_READY_DECISION
    assert payload["risk_acceptance_gates_verified"] is False


def test_blocks_source_exchange_or_live_flags() -> None:
    source = source_30t()
    source["approved_for_exchange_submit"] = True
    source["approved_for_live_real"] = True
    source["exchange_submit_performed"] = True
    payload = build_paper_promotion_review_snapshot(Settings(), source)
    assert payload["decision"] == SOURCE_30T_REQUIRED_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
