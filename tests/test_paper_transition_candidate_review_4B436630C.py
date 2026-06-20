from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_transition_candidate_review import (
    OPERATOR_EVIDENCE_REQUIRED_DECISION,
    READY_DECISION,
    evaluate_paper_transition_candidate_review,
)


def _base_30b_snapshot(*, approved: bool = False) -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30B",
        "decision": "PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_READY_REVIEW_ONLY_LIVE_REAL_BLOCKED" if approved else "PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED",
        "approved_for_paper_transition_operator_approval_gate": True,
        "approved_for_paper_transition_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "operator_approval_verified": approved,
        "sandbox_runtime_envelope_verified": True,
        "paper_dry_run_reconciliation_probe_verified": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "sandbox_runtime_envelope": {
            "runtime_envelope": "sandbox_only",
            "execution_mode": "dry_run",
            "market_type": "spot_demo",
            "base_url": "https://demo-api.binance.com",
            "auto_trade_on_signal": False,
            "live_trading_armed": False,
            "live_real_double_confirm": False,
            "max_open_orders": 1,
        },
        "paper_preflight_snapshot": {
            "risk_limits": {
                "capital_cap_usd": 100.0,
                "order_notional_cap_usd": 25.0,
                "max_daily_loss_usd": 5.0,
                "max_daily_trades_cap": 5,
                "kill_switch_enabled": True,
            }
        },
    }


def _approved_settings() -> Settings:
    return Settings(
        paper_transition_runtime_envelope_frozen=True,
        paper_transition_runtime_envelope_freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        paper_transition_final_risk_cap_verified=True,
    )


def test_default_30b_without_operator_approval_blocks_candidate_review() -> None:
    decision = evaluate_paper_transition_candidate_review(Settings(), _base_30b_snapshot(approved=False))

    assert decision.decision == OPERATOR_EVIDENCE_REQUIRED_DECISION
    assert decision.approved_for_paper_transition_candidate_review is False
    assert decision.approved_for_paper_transition_candidate is False
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert decision.paper_live_order_blocked is True
    assert decision.trading_action_performed is False


def test_approved_30b_plus_freeze_and_final_risk_cap_allows_review_only() -> None:
    decision = evaluate_paper_transition_candidate_review(_approved_settings(), _base_30b_snapshot(approved=True))

    assert decision.decision == READY_DECISION
    assert decision.approved_for_paper_transition_candidate_review is True
    assert decision.operator_approval_evidence_verified is True
    assert decision.sandbox_runtime_envelope_frozen is True
    assert decision.paper_risk_cap_final_verified is True
    assert decision.approved_for_paper_transition_candidate is False
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert decision.paper_live_order_blocked is True
    assert decision.trading_action_performed is False


def test_freeze_token_required_for_candidate_review() -> None:
    settings = Settings(
        paper_transition_runtime_envelope_frozen=True,
        paper_transition_runtime_envelope_freeze_token="WRONG",
        paper_transition_final_risk_cap_verified=True,
    )
    decision = evaluate_paper_transition_candidate_review(settings, _base_30b_snapshot(approved=True))

    assert decision.approved_for_paper_transition_candidate_review is False
    assert "RUNTIME_ENVELOPE_FREEZE_TOKEN_MISMATCH" in decision.reason_codes
    assert decision.approved_for_paper_candidate is False


def test_final_risk_cap_verification_required() -> None:
    settings = Settings(
        paper_transition_runtime_envelope_frozen=True,
        paper_transition_runtime_envelope_freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        paper_transition_final_risk_cap_verified=False,
    )
    decision = evaluate_paper_transition_candidate_review(settings, _base_30b_snapshot(approved=True))

    assert decision.approved_for_paper_transition_candidate_review is False
    assert "FINAL_RISK_CAP_NOT_OPERATOR_VERIFIED" in decision.reason_codes


def test_live_real_or_paper_enablement_in_source_blocks_review() -> None:
    source = _base_30b_snapshot(approved=True)
    source["approved_for_live_real"] = True
    source["approved_for_paper_candidate"] = True
    decision = evaluate_paper_transition_candidate_review(_approved_settings(), source)

    assert decision.approved_for_paper_transition_candidate_review is False
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert "SOURCE_30B_PAPER_CANDIDATE_UNEXPECTEDLY_APPROVED" in decision.reason_codes
    assert "SOURCE_30B_LIVE_REAL_UNEXPECTEDLY_APPROVED" in decision.reason_codes


def test_sandbox_envelope_must_stay_frozen_and_sandbox_only() -> None:
    source = _base_30b_snapshot(approved=True)
    envelope = source["sandbox_runtime_envelope"]
    assert isinstance(envelope, dict)
    envelope["execution_mode"] = "live_real"
    envelope["max_open_orders"] = 2
    decision = evaluate_paper_transition_candidate_review(_approved_settings(), source)

    assert decision.approved_for_paper_transition_candidate_review is False
    assert "RUNTIME_ENVELOPE_EXECUTION_MODE_LIVE_REAL_BLOCKED" in decision.reason_codes
    assert "RUNTIME_ENVELOPE_MAX_OPEN_ORDERS_MUST_EQUAL_ONE" in decision.reason_codes
