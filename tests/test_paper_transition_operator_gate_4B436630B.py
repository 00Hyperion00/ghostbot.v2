from __future__ import annotations

from dataclasses import replace

from tradebot.config import Settings
from tradebot.paper_transition_operator_gate import (
    APPROVAL_REQUIRED_DECISION,
    NOT_READY_DECISION,
    READY_DECISION,
    build_paper_transition_operator_gate_snapshot,
)

READY_PREFLIGHT = {
    "approved_for_no_order_to_paper_transition_preflight": True,
    "approved_for_paper_candidate": False,
    "approved_for_live_real": False,
    "paper_live_order_blocked": True,
    "decision": "PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED",
}


def _approved_settings() -> Settings:
    return Settings(
        paper_transition_operator_approved=True,
        paper_transition_operator_id="operator-1",
        paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        paper_transition_approval_issued_at_ms=1_000_000,
        paper_transition_approval_ttl_sec=900,
    )


def test_default_gate_requires_typed_operator_approval_without_enabling_paper() -> None:
    snapshot = build_paper_transition_operator_gate_snapshot(Settings(), READY_PREFLIGHT, now_ms=1_000_000)
    assert snapshot["decision"] == APPROVAL_REQUIRED_DECISION
    assert snapshot["approved_for_paper_transition_operator_approval_gate"] is True
    assert snapshot["approved_for_paper_transition_candidate"] is False
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["paper_live_order_blocked"] is True
    assert snapshot["trading_action_performed"] is False


def test_valid_typed_approval_promotes_transition_candidate_review_only() -> None:
    snapshot = build_paper_transition_operator_gate_snapshot(_approved_settings(), READY_PREFLIGHT, now_ms=1_000_100)
    assert snapshot["decision"] == READY_DECISION
    assert snapshot["operator_approval_verified"] is True
    assert snapshot["approved_for_paper_transition_candidate"] is True
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["paper_live_order_enablement_present"] is False


def test_expired_typed_approval_blocks_transition_candidate() -> None:
    settings = replace(_approved_settings(), paper_transition_approval_issued_at_ms=1_000_000, paper_transition_approval_ttl_sec=1)
    snapshot = build_paper_transition_operator_gate_snapshot(settings, READY_PREFLIGHT, now_ms=1_002_500)
    assert snapshot["decision"] == APPROVAL_REQUIRED_DECISION
    assert snapshot["operator_approval_verified"] is False
    assert "PAPER_TRANSITION_APPROVAL_TOKEN_EXPIRED" in snapshot["reason_codes"]


def test_live_real_runtime_envelope_is_fail_closed() -> None:
    settings = replace(_approved_settings(), execution_mode="live_real", market_type="spot_mainnet", base_url="https://api.binance.com")
    snapshot = build_paper_transition_operator_gate_snapshot(settings, READY_PREFLIGHT, now_ms=1_000_100)
    assert snapshot["decision"] == NOT_READY_DECISION
    assert snapshot["sandbox_runtime_envelope_verified"] is False
    assert snapshot["approved_for_paper_transition_candidate"] is False
    assert snapshot["approved_for_live_real"] is False


def test_dry_run_reconciliation_probe_must_not_perform_order_actions() -> None:
    settings = replace(_approved_settings(), paper_transition_dry_run_probe_order_actions_performed=True)
    snapshot = build_paper_transition_operator_gate_snapshot(settings, READY_PREFLIGHT, now_ms=1_000_100)
    assert snapshot["decision"] == NOT_READY_DECISION
    assert snapshot["paper_dry_run_reconciliation_probe_verified"] is False
    assert "PAPER_DRY_RUN_RECONCILIATION_PROBE_PERFORMED_ORDER_ACTION" in snapshot["reason_codes"]


def test_missing_30a_preflight_blocks_transition() -> None:
    snapshot = build_paper_transition_operator_gate_snapshot(_approved_settings(), {"approved_for_no_order_to_paper_transition_preflight": False}, now_ms=1_000_100)
    assert snapshot["decision"] == NOT_READY_DECISION
    assert snapshot["paper_candidate_preflight_ready"] is False
    assert snapshot["approved_for_paper_transition_candidate"] is False
