from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_candidate_gate import (
    PAPER_CANDIDATE_PREFLIGHT_CONTRACT_VERSION,
    build_paper_candidate_preflight_snapshot,
    evaluate_exchange_sandbox_isolation,
    evaluate_paper_candidate_preflight,
    evaluate_paper_risk_limits,
)


def ready_snapshot() -> dict[str, object]:
    return {
        "decision": "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
        "evidence_complete": True,
        "approved_for_paper_candidate_preflight": True,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
    }


def test_default_preflight_ready_but_operator_approval_required() -> None:
    settings = Settings()
    decision = evaluate_paper_candidate_preflight(settings, ready_snapshot())
    assert decision.contract_version == PAPER_CANDIDATE_PREFLIGHT_CONTRACT_VERSION
    assert decision.approved_for_no_order_to_paper_transition_preflight is True
    assert decision.approved_for_paper_transition_candidate is False
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert decision.paper_live_order_blocked is True


def test_operator_approval_promotes_only_transition_candidate_review_not_paper_enablement() -> None:
    settings = Settings(
        paper_transition_operator_approved=True,
        paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
    )
    decision = evaluate_paper_candidate_preflight(settings, ready_snapshot())
    assert decision.approved_for_paper_transition_candidate is True
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert decision.trading_action_performed is False


def test_live_real_or_mainnet_blocks_sandbox_isolation() -> None:
    settings = Settings(execution_mode="live_real", market_type="spot_mainnet", base_url="https://api.binance.com")
    sandbox = evaluate_exchange_sandbox_isolation(settings)
    assert sandbox.ok is False
    assert "EXECUTION_MODE_LIVE_REAL_BLOCKED" in sandbox.reason_codes
    assert "MARKET_TYPE_NOT_SANDBOX_ALLOWED" in sandbox.reason_codes


def test_invalid_risk_caps_block_preflight() -> None:
    settings = Settings(paper_transition_capital_cap_usd=10.0, paper_order_notional_cap_usd=25.0)
    limits = evaluate_paper_risk_limits(settings)
    assert limits.ok is False
    assert "PAPER_ORDER_CAP_EXCEEDS_CAPITAL_CAP" in limits.reason_codes
    decision = evaluate_paper_candidate_preflight(settings, ready_snapshot())
    assert decision.approved_for_no_order_to_paper_transition_preflight is False


def test_incomplete_production_readiness_blocks_preflight() -> None:
    settings = Settings()
    snapshot = {"decision": "PRODUCTION_READINESS_CONSOLIDATION_NOT_READY", "evidence_complete": False}
    decision = evaluate_paper_candidate_preflight(settings, snapshot)
    assert decision.approved_for_no_order_to_paper_transition_preflight is False
    assert "PRODUCTION_READINESS_CONSOLIDATION_REQUIRED" in decision.reason_codes


def test_snapshot_contains_fail_closed_mutation_flags() -> None:
    settings = Settings()
    snapshot = build_paper_candidate_preflight_snapshot(settings, ready_snapshot())
    assert snapshot["paper_candidate_preflight"] is True
    assert snapshot["runtime_overlay_activation_performed"] is False
    assert snapshot["paper_live_order_enablement_present"] is False
    assert snapshot["hyp006_strategy_threshold_mutation_performed"] is False
