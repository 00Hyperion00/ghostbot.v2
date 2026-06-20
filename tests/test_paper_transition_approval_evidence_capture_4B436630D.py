from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_transition_approval_evidence_capture import (
    INPUT_REQUIRED_DECISION,
    READY_DECISION,
    build_from_operator_inputs,
    build_operator_approval_evidence_capture_snapshot,
    build_approval_capture_settings,
)

NOW_MS = 1_800_000_000_000


def test_default_capture_requires_operator_input() -> None:
    payload = build_from_operator_inputs(now_ms=NOW_MS)
    assert payload["decision"] == INPUT_REQUIRED_DECISION
    assert payload["approved_for_operator_approval_evidence_capture"] is False
    assert payload["approved_for_paper_transition_candidate_review"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_valid_operator_approval_capture_is_review_only() -> None:
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
    assert payload["trading_action_performed"] is False
    assert payload["source_30b_ready"] is True
    assert payload["source_30c_review_ready"] is True


def test_expired_ttl_blocks_capture() -> None:
    settings = build_approval_capture_settings(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        issued_at_ms=NOW_MS - 901_000,
        ttl_sec=900,
    )
    payload = build_operator_approval_evidence_capture_snapshot(settings, now_ms=NOW_MS)
    assert payload["decision"] != READY_DECISION
    assert "TYPED_APPROVAL_TTL_EXPIRED" in payload["reason_codes"]
    assert payload["approved_for_paper_candidate"] is False


def test_freeze_token_mismatch_blocks_capture() -> None:
    payload = build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="WRONG",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    assert payload["decision"] != READY_DECISION
    assert "RUNTIME_ENVELOPE_FREEZE_TOKEN_MISMATCH" in payload["reason_codes"]
    assert payload["approved_for_live_real"] is False


def test_unverified_final_risk_cap_blocks_capture() -> None:
    payload = build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=False,
        now_ms=NOW_MS,
    )
    assert payload["decision"] != READY_DECISION
    assert "FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR" in payload["reason_codes"]
    assert payload["paper_order_enablement_still_blocked"] is True


def test_order_and_live_real_never_enabled_even_when_ready() -> None:
    payload = build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    forbidden = (
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "runtime_overlay_activation_performed",
        "trading_action_performed",
        "order_actions_performed",
        "paper_live_order_enablement_present",
    )
    for key in forbidden:
        assert payload[key] is False
