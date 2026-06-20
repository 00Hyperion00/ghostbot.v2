from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_execution_reconciliation_gate import (
    READY_DECISION,
    SQLITE_MIRROR_REQUIRED_DECISION,
    build_paper_sandbox_execution_reconciliation_snapshot,
)


def _report() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_dry_run_execution_gate": True,
        "approved_for_30m_order_envelope_consumption": True,
        "approved_for_internal_paper_execution_simulation": True,
        "approved_for_paper_execution_ledger_append": True,
        "approved_for_paper_sandbox_dry_run_execution": True,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def _event() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "event_id": "paper-exec-4B436630N-test",
        "event_type": "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "simulated_fee_bps": 10.0,
        "simulated_fee_usd": 0.025,
        "quote_balance_delta_usd": -25.025,
        "base_balance_delta": 0.01,
        "signed_position_qty_delta": 0.01,
        "base_asset": "ETH",
        "quote_asset": "USDT",
        "exchange_submit_performed": False,
        "submitted_to_exchange": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def test_30o_ready_writes_sqlite_mirror(tmp_path: Path) -> None:
    snapshot = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        _report(),
        _event(),
        source_report_path="30n_ready.json",
        ledger_path=str(tmp_path / "ledger.jsonl"),
        ledger_rows=1,
        write_sqlite_mirror=True,
        sqlite_path=tmp_path / "audit.sqlite",
    )
    assert snapshot["decision"] == READY_DECISION
    assert snapshot["approved_for_paper_sandbox_execution_reconciliation_gate"] is True
    assert snapshot["approved_for_mismatch_zero_proof"] is True
    assert snapshot["mismatch_count"] == 0
    assert snapshot["sqlite_audit_mirror_verified"] is True


def test_30o_blocks_until_sqlite_mirror_written(tmp_path: Path) -> None:
    snapshot = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        _report(),
        _event(),
        source_report_path="30n_ready.json",
        ledger_path=str(tmp_path / "ledger.jsonl"),
        ledger_rows=1,
        write_sqlite_mirror=False,
        sqlite_path=tmp_path / "audit.sqlite",
    )
    assert snapshot["decision"] == SQLITE_MIRROR_REQUIRED_DECISION
    assert snapshot["approved_for_sqlite_audit_mirror"] is False
    assert snapshot["approved_for_paper_sandbox_execution_reconciliation_gate"] is False


def test_30o_detects_mismatch(tmp_path: Path) -> None:
    event = _event()
    event["quote_balance_delta_usd"] = -1.0
    snapshot = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        _report(),
        event,
        source_report_path="30n_ready.json",
        ledger_path=str(tmp_path / "ledger.jsonl"),
        ledger_rows=1,
        write_sqlite_mirror=True,
        sqlite_path=tmp_path / "audit.sqlite",
    )
    assert snapshot["approved_for_mismatch_zero_proof"] is False
    assert snapshot["mismatch_count"] >= 1
    assert snapshot["approved_for_paper_sandbox_execution_reconciliation_gate"] is False


def test_30o_never_enables_exchange_or_live_real(tmp_path: Path) -> None:
    snapshot = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        _report(),
        _event(),
        source_report_path="30n_ready.json",
        ledger_path=str(tmp_path / "ledger.jsonl"),
        ledger_rows=1,
        write_sqlite_mirror=True,
        sqlite_path=tmp_path / "audit.sqlite",
    )
    assert snapshot["approved_for_exchange_submit"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["exchange_submit_performed"] is False
    assert snapshot["trading_action_performed"] is False
    assert snapshot["paper_live_order_enablement_present"] is False
