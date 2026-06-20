from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_execution_readiness_lock import (
    OPERATOR_LOCK_REQUIRED_DECISION,
    READY_DECISION,
    SOURCE_30G_REQUIRED_DECISION,
    build_operator_lock_settings,
    build_paper_sandbox_dry_run_execution_readiness_lock_snapshot,
)

NOW_MS = 1_800_000_000_000


def source_30g_ready() -> dict[str, object]:
    return {
        "ok": True,
        "contract_version": "4B.4.3.6.6.30G",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_CANDIDATE_GATE_READY_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_execution_candidate_gate": True,
        "approved_for_paper_sandbox_dry_run_execution_candidate": True,
        "approved_for_single_simulated_paper_intent": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "no_exchange_submit": {
            "submitted_to_exchange": False,
            "exchange_submit_performed": False,
            "network_submit_attempted": False,
            "exchange_order_id": None,
            "exchange_client_order_id": None,
        },
    }


def test_default_requires_explicit_operator_dry_run_lock() -> None:
    payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(Settings(), source_30g_ready(), now_ms=NOW_MS)
    assert payload["decision"] == OPERATOR_LOCK_REQUIRED_DECISION
    assert payload["source_30g_candidate_gate_verified"] is True
    assert payload["operator_explicit_dry_run_lock_verified"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution_readiness_lock"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_explicit_lock_readiness_is_ready_but_execution_disabled() -> None:
    settings = build_operator_lock_settings(
        operator_id="operator-30h",
        lock_token="LOCK_PAPER_SANDBOX_DRY_RUN_READINESS",
        issue_lock=True,
        issued_at_ms=NOW_MS,
        ttl_sec=900,
    )
    payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(settings, source_30g_ready(), now_ms=NOW_MS)
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_execution_readiness_lock"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution_readiness_candidate"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["paper_execution_still_disabled_verified"] is True


def test_bad_30g_source_blocks_before_lock() -> None:
    bad = source_30g_ready()
    bad["approved_for_exchange_submit"] = True
    settings = build_operator_lock_settings(
        operator_id="operator-30h",
        lock_token="LOCK_PAPER_SANDBOX_DRY_RUN_READINESS",
        issue_lock=True,
        issued_at_ms=NOW_MS,
    )
    payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(settings, bad, now_ms=NOW_MS)
    assert payload["decision"] == SOURCE_30G_REQUIRED_DECISION
    assert payload["source_30g_candidate_gate_verified"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution_readiness_lock"] is False


def test_expired_operator_lock_blocks_readiness() -> None:
    settings = build_operator_lock_settings(
        operator_id="operator-30h",
        lock_token="LOCK_PAPER_SANDBOX_DRY_RUN_READINESS",
        issue_lock=True,
        issued_at_ms=NOW_MS - 901_000,
        ttl_sec=900,
    )
    payload = build_paper_sandbox_dry_run_execution_readiness_lock_snapshot(settings, source_30g_ready(), now_ms=NOW_MS)
    assert payload["decision"] == OPERATOR_LOCK_REQUIRED_DECISION
    assert payload["operator_explicit_dry_run_lock_verified"] is False
    assert "OPERATOR_DRY_RUN_LOCK_TTL_EXPIRED" in payload["reason_codes"]
