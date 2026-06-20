from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_dry_run_internal_execution_harness import (
    READY_DECISION,
    SOURCE_30H_REQUIRED_DECISION,
    build_paper_sandbox_dry_run_internal_execution_harness_snapshot,
)

NOW_MS = 1_800_000_000_000


def _ready_30h_snapshot() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30H",
        "decision": "PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_execution_readiness_lock": True,
        "approved_for_paper_sandbox_dry_run_execution_readiness_candidate": True,
        "approved_for_operator_explicit_dry_run_lock": True,
        "approved_for_exchange_submit_hard_block_audit": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_execution_still_disabled_verified": True,
        "exchange_submit_performed": False,
        "paper_order_enablement_still_blocked": True,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
        "exchange_submit_hard_block_audit": {
            "approved_for_exchange_submit": False,
            "submitted_to_exchange": False,
            "exchange_submit_performed": False,
            "network_submit_attempted": False,
            "exchange_order_id_present": False,
            "exchange_client_order_id_present": False,
        },
        "source_30g_snapshot": {
            "dry_run_only_runtime_envelope": {
                "runtime_envelope": "sandbox_only",
                "execution_mode": "dry_run",
                "market_type": "spot_demo",
                "base_url": "https://demo-api.binance.com",
                "auto_trade_on_signal": False,
                "live_trading_armed": False,
                "live_real_double_confirm": False,
            },
            "single_simulated_paper_intent": {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quote_notional_usd": 25.0,
            },
        },
    }


def test_30i_missing_source_blocks() -> None:
    payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
        Settings(),
        {},
        ledger_path="reports/test_ledger.jsonl",
        append_ledger=False,
        now_ms=NOW_MS,
    )
    assert payload["decision"] == SOURCE_30H_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_internal_execution_harness"] is False
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False


def test_30i_ready_internal_harness_appends_simulated_fill_without_exchange_submit(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
        Settings(),
        _ready_30h_snapshot(),
        source_report_path="reports/production_hardening/30h_ready.json",
        ledger_path=ledger_path,
        append_ledger=True,
        now_ms=NOW_MS,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_dry_run_internal_execution_harness"] is True
    assert payload["approved_for_internal_only_execution_harness"] is True
    assert payload["approved_for_simulated_fill_ledger_append"] is True
    assert payload["simulated_fill_ledger_append_performed"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["trading_action_performed"] is False
    assert payload["exchange_submit_performed"] is False
    assert ledger_path.exists()
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "internal_simulated_fill_no_exchange_submit" in lines[0]


def test_30i_bad_source_exchange_submit_blocks(tmp_path: Path) -> None:
    source = _ready_30h_snapshot()
    source["exchange_submit_performed"] = True
    payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
        Settings(),
        source,
        ledger_path=tmp_path / "ledger.jsonl",
        append_ledger=True,
        now_ms=NOW_MS,
    )
    assert payload["decision"] == SOURCE_30H_REQUIRED_DECISION
    assert payload["approved_for_simulated_fill_ledger_append"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_30i_runtime_harness_rejects_live_flags(tmp_path: Path) -> None:
    settings = Settings(live_trading_armed=True)
    source = _ready_30h_snapshot()
    source["source_30g_snapshot"] = {"dry_run_only_runtime_envelope": {"execution_mode": "dry_run", "runtime_envelope": "sandbox_only", "market_type": "spot_demo", "base_url": "https://demo-api.binance.com", "live_trading_armed": True}}
    payload = build_paper_sandbox_dry_run_internal_execution_harness_snapshot(
        settings,
        source,
        ledger_path=tmp_path / "ledger.jsonl",
        append_ledger=True,
        now_ms=NOW_MS,
    )
    assert payload["decision"] == "PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_NOT_READY_LIVE_REAL_BLOCKED"
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_live_real"] is False
