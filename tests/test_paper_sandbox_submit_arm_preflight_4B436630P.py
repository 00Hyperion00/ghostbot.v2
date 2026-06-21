from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_submit_arm_preflight import (
    READY_DECISION,
    SANDBOX_READINESS_NOT_READY_DECISION,
    SOURCE_30O_REQUIRED_DECISION,
    build_paper_sandbox_submit_arm_preflight_snapshot,
)


def source_30o() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_execution_reconciliation_gate": True,
        "approved_for_30n_ledger_consumption": True,
        "mismatch_count": 0,
        "mismatch_zero": True,
        "sqlite_mirror_ok": True,
        "ledger_consumed": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_30p_ready_submit_arm_preflight_submit_still_blocked() -> None:
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), source_30o())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_submit_arm_preflight"] is True
    assert payload["approved_for_order_request_skeleton_build"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_sandbox_canary_submit"] is False
    assert payload["submit_order_still_blocked"] is True


def test_30p_blocks_bad_source_reconciliation() -> None:
    bad = source_30o()
    bad["mismatch_count"] = 1
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), bad)
    assert payload["decision"] == SOURCE_30O_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_submit_arm_preflight"] is False
    assert payload["approved_for_exchange_submit"] is False


def test_30p_blocks_min_notional_failure() -> None:
    settings = Settings(order_notional_usd=1.0)
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(settings, source_30o())
    assert payload["decision"] == SANDBOX_READINESS_NOT_READY_DECISION
    assert payload["approved_for_min_notional_check"] is False
    assert payload["approved_for_exchange_submit"] is False


def test_30p_blocks_kill_switch_disabled() -> None:
    settings = Settings(paper_kill_switch_enabled=False)
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(settings, source_30o())
    assert payload["decision"] == SANDBOX_READINESS_NOT_READY_DECISION
    assert payload["approved_for_kill_switch_check"] is False
    assert payload["approved_for_live_real"] is False


def test_30p_keeps_no_exchange_submit_no_live_real() -> None:
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), source_30o())
    skeleton = payload["sandbox_submit_readiness"]["order_request_skeleton"]
    assert skeleton["submit_to_exchange"] is False
    assert skeleton["exchange_submit_performed"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["trading_action_performed"] is False
