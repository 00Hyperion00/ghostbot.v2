from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_execution_reconciliation_gate import READY_DECISION, build_paper_sandbox_execution_reconciliation_snapshot


def event() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "event_type": "internal_paper_sandbox_dry_run_execution_simulated_fill_no_exchange_submit",
        "event_id": "paper-exec-4B436630N-h6-test",
        "symbol": "ETHUSDT",
        "base_asset": "ETH",
        "quote_asset": "USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "signed_position_qty_delta": 0.01,
        "quote_balance_delta_usd": -25.025,
        "base_balance_delta": 0.01,
        "simulated_fee_bps": 10.0,
        "simulated_fee_usd": 0.025,
        "network_submit_attempted": False,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "live_real_approved": False,
    }


def source(ledger_path: str) -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30N",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_READY_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_dry_run_execution_gate": True,
        "approved_for_30m_order_envelope_consumption": True,
        "approved_for_internal_paper_execution_simulation": True,
        "approved_for_paper_execution_ledger_append": True,
        "approved_for_paper_sandbox_dry_run_execution": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_execution_ledger_path": ledger_path,
        "internal_paper_execution_simulation": {"event": event(), "ledger_path": ledger_path},
    }


def test_h6_file_ledger_reconciles_and_mirrors_sqlite(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    sqlite_path = tmp_path / "mirror.db"
    ledger.write_text(json.dumps(event(), sort_keys=True) + "\n", encoding="utf-8")
    payload = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        source(str(ledger)),
        ledger_path=ledger,
        sqlite_path=sqlite_path,
        reports_dir=tmp_path,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["ledger_consumed"] is True
    assert payload["approved_for_mismatch_zero_proof"] is True
    assert payload["approved_for_sqlite_audit_mirror"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_h6_direct_ledger_event_signature_reconciles(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "direct.db"
    payload = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        source("DIRECT_LEDGER_EVENT_PROBE"),
        ledger_event=event(),
        sqlite_path=sqlite_path,
        reports_dir=tmp_path,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["ledger_consumed"] is True
    assert payload["approved_for_sqlite_audit_mirror"] is True
    assert payload["exchange_submit_performed"] is False


def test_h6_blocks_exchange_submit_event(tmp_path: Path) -> None:
    bad = event()
    bad["submitted_to_exchange"] = True
    payload = build_paper_sandbox_execution_reconciliation_snapshot(
        Settings(),
        source("DIRECT_LEDGER_EVENT_PROBE"),
        ledger_event=bad,
        sqlite_path=tmp_path / "bad.db",
        reports_dir=tmp_path,
    )
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False
