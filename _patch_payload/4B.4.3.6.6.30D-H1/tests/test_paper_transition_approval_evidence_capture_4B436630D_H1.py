from __future__ import annotations

from tradebot.paper_transition_approval_evidence_capture import (
    INPUT_REQUIRED_DECISION,
    READY_DECISION,
    build_from_operator_inputs,
)

NOW_MS = 1_800_000_000_000


def test_30d_h1_default_capture_no_settings_clone_type_error() -> None:
    payload = build_from_operator_inputs(now_ms=NOW_MS)
    assert payload["decision"] == INPUT_REQUIRED_DECISION
    assert payload["approved_for_operator_approval_evidence_capture"] is False
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_30d_h1_explicit_capture_ready_but_no_order_or_live_enablement() -> None:
    payload = build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_operator_approval_evidence_capture"] is True
    assert payload["approved_for_paper_transition_candidate_review"] is True
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["runtime_activation_blocked"] is True
    assert payload["paper_live_order_blocked"] is True
    assert payload["training_reload_blocked"] is True
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False
    assert payload["paper_live_order_enablement_present"] is False
