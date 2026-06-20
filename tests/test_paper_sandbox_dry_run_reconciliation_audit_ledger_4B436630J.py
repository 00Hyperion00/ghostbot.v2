from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_reconciliation_audit_ledger import (
    READY_DECISION,
    build_from_latest_30i_evidence,
    evaluate_no_exchange_submit,
    evaluate_order_fill_position_balance_reconciliation,
)


def _write_30i_evidence(tmp_path: Path) -> tuple[Path, Path, dict[str, object], dict[str, object]]:
    reports = tmp_path / "reports" / "production_hardening"
    reports.mkdir(parents=True, exist_ok=True)
    event: dict[str, object] = {
        "event_id": "sim-fill-4B436630I-test",
        "contract_version": "4B.4.3.6.6.30I",
        "event_type": "internal_simulated_fill_no_exchange_submit",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 25.0,
        "simulated_fill_price_usd": 2500.0,
        "simulated_fill_qty": 0.01,
        "submitted_to_exchange": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "exchange_order_id": None,
        "exchange_client_order_id": None,
        "paper_candidate_approved": False,
        "live_real_approved": False,
    }
    ledger_path = reports / "4B436630I_internal_simulated_fill_ledger.jsonl"
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    source: dict[str, object] = {
        "contract_version": "4B.4.3.6.6.30I",
        "decision": "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_internal_execution_harness": True,
        "approved_for_internal_only_execution_harness": True,
        "approved_for_simulated_fill_ledger_append": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "simulated_fill_ledger_append_performed": True,
        "paper_order_enablement_still_blocked": True,
        "paper_live_order_enablement_present": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "simulated_fill_ledger_append": {
            "ok": True,
            "required": True,
            "append_performed": True,
            "ledger_path": ledger_path.as_posix(),
            "ledger_event_id": event["event_id"],
            "event": event,
        },
    }
    source_path = reports / "4B436630I_paper_sandbox_dry_run_internal_execution_harness_20260101T000000Z_ready.json"
    source_path.write_text(json.dumps(source, sort_keys=True, indent=2), encoding="utf-8", newline="\n")
    return reports, ledger_path, source, event


def test_30j_ready_consumes_30i_ledger_and_reconciles_mismatch_zero(tmp_path: Path) -> None:
    reports, ledger_path, _source, _event = _write_30i_evidence(tmp_path)
    sqlite_path = tmp_path / "mirror.db"
    settings = Settings(
        paper_sandbox_dry_run_simulated_fill_ledger_path=ledger_path.as_posix(),
        paper_sandbox_dry_run_reconciliation_sqlite_path=sqlite_path.as_posix(),
    )
    payload = build_from_latest_30i_evidence(settings=settings, reports_dir=reports, sqlite_path=sqlite_path)
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_30i_simulated_fill_ledger_consumption"] is True
    assert payload["approved_for_order_fill_position_balance_reconciliation"] is True
    assert payload["approved_for_mismatch_zero_proof"] is True
    assert payload["mismatch_count"] == 0
    assert payload["reconciliation"]["notional_mismatch"] <= payload["reconciliation"]["tolerance"]


def test_30j_sqlite_audit_mirror_records_order_fill_position_balance(tmp_path: Path) -> None:
    reports, ledger_path, _source, _event = _write_30i_evidence(tmp_path)
    sqlite_path = tmp_path / "mirror.db"
    settings = Settings(
        paper_sandbox_dry_run_simulated_fill_ledger_path=ledger_path.as_posix(),
        paper_sandbox_dry_run_reconciliation_sqlite_path=sqlite_path.as_posix(),
    )
    payload = build_from_latest_30i_evidence(settings=settings, reports_dir=reports, sqlite_path=sqlite_path)
    mirror = payload["sqlite_audit_mirror"]
    assert payload["approved_for_sqlite_audit_mirror"] is True
    assert mirror["orders_count"] >= 1
    assert mirror["fills_count"] >= 1
    assert mirror["positions_count"] >= 1
    assert mirror["balance_snapshots_count"] >= 2
    assert mirror["audit_snapshot_ok"] is True


def test_30j_keeps_no_exchange_submit_and_paper_candidate_blocked(tmp_path: Path) -> None:
    reports, ledger_path, _source, _event = _write_30i_evidence(tmp_path)
    sqlite_path = tmp_path / "mirror.db"
    settings = Settings(
        paper_sandbox_dry_run_simulated_fill_ledger_path=ledger_path.as_posix(),
        paper_sandbox_dry_run_reconciliation_sqlite_path=sqlite_path.as_posix(),
    )
    payload = build_from_latest_30i_evidence(settings=settings, reports_dir=reports, sqlite_path=sqlite_path)
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["no_exchange_submit_verified"] is True
    assert payload["paper_candidate_still_blocked_verified"] is True


def test_30j_blocks_if_exchange_submit_seen_in_ledger(tmp_path: Path) -> None:
    reports, ledger_path, source, event = _write_30i_evidence(tmp_path)
    event["exchange_submit_performed"] = True
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    source["simulated_fill_ledger_append"] = {"ledger_path": ledger_path.as_posix(), "ledger_event_id": event["event_id"], "event": event}
    (reports / "4B436630I_paper_sandbox_dry_run_internal_execution_harness_20260101T000000Z_ready.json").write_text(
        json.dumps(source, sort_keys=True, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    payload = build_from_latest_30i_evidence(
        settings=Settings(paper_sandbox_dry_run_simulated_fill_ledger_path=ledger_path.as_posix()),
        reports_dir=reports,
        sqlite_path=tmp_path / "mirror.db",
    )
    assert payload["decision"] != READY_DECISION
    assert payload["no_exchange_submit_verified"] is False
