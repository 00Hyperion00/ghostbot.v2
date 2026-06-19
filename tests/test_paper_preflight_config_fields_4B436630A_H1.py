from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_candidate_gate import evaluate_paper_candidate_preflight


def _production_ready() -> dict[str, object]:
    return {
        "decision": "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
        "evidence_complete": True,
        "approved_for_paper_candidate_preflight": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
    }


def test_30a_paper_preflight_config_fields_exist() -> None:
    settings = Settings()
    assert settings.paper_candidate_preflight_enabled is True
    assert settings.paper_transition_operator_approval_required is True
    assert settings.paper_transition_operator_approved is False
    assert settings.paper_transition_confirmation_phrase == "CONFIRM_PAPER_TRANSITION_CANDIDATE"
    assert settings.paper_exchange_sandbox_required is True
    assert settings.paper_transition_capital_cap_usd >= settings.paper_order_notional_cap_usd
    assert settings.paper_kill_switch_enabled is True


def test_operator_approval_still_review_only_not_paper_enablement() -> None:
    settings = Settings(
        paper_transition_operator_approved=True,
        paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
    )
    decision = evaluate_paper_candidate_preflight(settings, _production_ready())
    assert decision.approved_for_paper_transition_candidate is True
    assert decision.approved_for_paper_candidate is False
    assert decision.approved_for_live_real is False
    assert decision.trading_action_performed is False


def test_invalid_caps_still_block_preflight() -> None:
    settings = Settings(paper_transition_capital_cap_usd=10.0, paper_order_notional_cap_usd=25.0)
    decision = evaluate_paper_candidate_preflight(settings, _production_ready())
    assert decision.approved_for_no_order_to_paper_transition_preflight is False
    assert "PAPER_ORDER_CAP_EXCEEDS_CAPITAL_CAP" in decision.reason_codes
