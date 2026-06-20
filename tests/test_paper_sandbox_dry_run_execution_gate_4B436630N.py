from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_execution_gate import (
    AUTHORIZATION_REQUIRED_DECISION,
    READY_DECISION,
    build_paper_sandbox_dry_run_execution_snapshot,
)


def source_30m() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30M",
        "decision": "PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_execution_preflight": True,
        "approved_for_30l_candidate_unlock_consumption": True,
        "approved_for_paper_sandbox_dry_run_authorization": True,
        "approved_for_order_envelope_build": True,
        "order_envelope_built": True,
        "order_envelope_written": True,
        "approved_for_paper_candidate": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def envelope() -> dict[str, object]:
    return {
        "envelope_id": "order-envelope-test",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "runtime_envelope": "sandbox_only",
        "execution_mode": "dry_run",
        "market_type": "spot_demo",
    }


def test_default_requires_execution_authorization(tmp_path: Path) -> None:
    payload = build_paper_sandbox_dry_run_execution_snapshot(
        Settings(),
        source_30m(),
        order_envelope=envelope(),
        ledger_path=tmp_path / "ledger.jsonl",
        now_ms=1_781_980_000_000,
    )
    assert payload["decision"] == AUTHORIZATION_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_execution_gate"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_ready_appends_internal_paper_execution_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    payload = build_paper_sandbox_dry_run_execution_snapshot(
        Settings(),
        source_30m(),
        order_envelope=envelope(),
        operator_id="operator-30n",
        authorization_token="AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION",
        issue_execution_authorization=True,
        append_ledger=True,
        ledger_path=ledger,
        now_ms=1_781_980_001_000,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_execution_gate"] is True
    assert payload["approved_for_internal_paper_execution_simulation"] is True
    assert payload["approved_for_paper_execution_ledger_append"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is True
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["event_type"] == "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit"
    assert rows[0]["submitted_to_exchange"] is False
    assert rows[0]["exchange_submit_performed"] is False


def test_ready_keeps_no_exchange_submit_no_live_real(tmp_path: Path) -> None:
    payload = build_paper_sandbox_dry_run_execution_snapshot(
        Settings(),
        source_30m(),
        order_envelope=envelope(),
        operator_id="operator-30n",
        authorization_token="AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION",
        issue_execution_authorization=True,
        append_ledger=True,
        ledger_path=tmp_path / "ledger.jsonl",
        now_ms=1_781_980_002_000,
    )
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_rejects_source_with_exchange_submit_enabled(tmp_path: Path) -> None:
    source = source_30m()
    source["approved_for_exchange_submit"] = True
    payload = build_paper_sandbox_dry_run_execution_snapshot(
        Settings(),
        source,
        order_envelope=envelope(),
        operator_id="operator-30n",
        authorization_token="AUTHORIZE_INTERNAL_PAPER_SANDBOX_DRY_RUN_EXECUTION",
        issue_execution_authorization=True,
        append_ledger=True,
        ledger_path=tmp_path / "ledger.jsonl",
        now_ms=1_781_980_003_000,
    )
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert not (tmp_path / "ledger.jsonl").exists()
