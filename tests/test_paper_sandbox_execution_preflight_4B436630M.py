
from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_execution_preflight import (
    AUTHORIZATION_REQUIRED_DECISION,
    READY_DECISION,
    build_paper_sandbox_execution_preflight_snapshot,
)


def source_30l_ready() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30L",
        "decision": "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_candidate_unlock_gate": True,
        "approved_for_explicit_paper_candidate_unlock": True,
        "approved_for_sandbox_only_order_enablement_preflight": True,
        "approved_for_paper_sandbox_candidate": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "sandbox_order_enablement_preflight": {
            "order_notional_usd": 25.0,
            "order_notional_cap_usd": 25.0,
            "capital_cap_usd": 100.0,
            "max_daily_loss_usd": 5.0,
            "max_daily_trades_cap": 5,
            "max_open_orders": 1,
        },
    }


def test_30m_default_requires_authorization() -> None:
    payload = build_paper_sandbox_execution_preflight_snapshot(Settings(), source_30l_ready(), now_ms=1_800_000_000_000)
    assert payload["decision"] == AUTHORIZATION_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_execution_preflight"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_30m_ready_builds_order_envelope_without_exchange_submit(tmp_path: Path) -> None:
    envelope_path = tmp_path / "order_envelope.json"
    payload = build_paper_sandbox_execution_preflight_snapshot(
        Settings(),
        source_30l_ready(),
        operator_id="operator-30m",
        authorization_token="AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT",
        issue_dry_run_authorization=True,
        envelope_path=envelope_path,
        write_envelope=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_order_envelope_build"] is True
    assert payload["order_envelope_built"] is True
    assert payload["order_envelope_written"] is True
    assert envelope_path.exists()
    envelope = payload["order_envelope"]["envelope"]
    assert envelope["submitted_to_exchange"] is False
    assert envelope["exchange_submit_performed"] is False
    assert envelope["network_submit_attempted"] is False


def test_30m_preserves_candidate_only_no_execution() -> None:
    payload = build_paper_sandbox_execution_preflight_snapshot(
        Settings(),
        source_30l_ready(),
        operator_id="operator-30m",
        authorization_token="AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT",
        issue_dry_run_authorization=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["approved_for_paper_sandbox_candidate"] is True
    assert payload["approved_for_paper_candidate"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_30m_blocks_non_sandbox_settings() -> None:
    settings = Settings(execution_mode="live", market_type="spot", live_trading_armed=True)
    payload = build_paper_sandbox_execution_preflight_snapshot(
        settings,
        source_30l_ready(),
        operator_id="operator-30m",
        authorization_token="AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT",
        issue_dry_run_authorization=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_order_envelope_build"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
