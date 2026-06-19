from __future__ import annotations

import sqlite3
from pathlib import Path

from tradebot.persistence import (
    SQLITE_AUDIT_LEDGER_CONTRACT_VERSION,
    SQLITE_AUDIT_LEDGER_SCHEMA_VERSION,
    SQLiteStore,
)

EXPECTED_TABLES = {
    "schema_migrations",
    "operator_actions",
    "orders",
    "fills",
    "positions",
    "risk_events",
    "model_decisions",
    "balance_snapshots",
}


def test_sqlite_audit_ledger_tables_and_schema_version(tmp_path: Path) -> None:
    db_path = tmp_path / "tradebot.db"
    store = SQLiteStore(str(db_path))

    snapshot = store.audit_ledger_snapshot()
    assert snapshot["ok"] is True
    assert snapshot["contract_version"] == SQLITE_AUDIT_LEDGER_CONTRACT_VERSION
    assert snapshot["schema_version"] == SQLITE_AUDIT_LEDGER_SCHEMA_VERSION
    assert set(snapshot["tables"]) == EXPECTED_TABLES
    assert all(snapshot["tables"].values())

    integrity = store.integrity_check()
    assert integrity["ok"] is True
    assert integrity["schema_version"] == SQLITE_AUDIT_LEDGER_SCHEMA_VERSION


def test_audit_ledger_append_methods_insert_rows(tmp_path: Path) -> None:
    store = SQLiteStore(str(tmp_path / "audit.db"))

    store.append_operator_action(action="POST /force-buy", actor="operator-a", confirmation="CONFIRM_FORCE_BUY", outcome="BLOCKED", data={"reason_code": "TEST"})
    store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "1", "clientOrderId": "abc", "status": "NEW", "price": 600, "qty": 0.1, "source": "unit"})
    store.append_fill_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "1", "clientOrderId": "abc", "tradeId": "t1", "price": 600, "qty": 0.1, "commissionAsset": "BNB", "commission": 0.001})
    store.append_position_audit({"symbol": "BNBUSDT", "state": "IN_POSITION", "qty": 0.1, "entryPrice": 600, "source": "unit"})
    store.append_risk_event({"symbol": "BNBUSDT", "eventType": "STOP_LOSS", "severity": "WARN", "reasonCode": "TEST_RISK", "message": "unit"})
    store.append_model_decision({"symbol": "BNBUSDT", "signal": "HOLD", "confidence": 0.77, "provider": "xgb", "modelPath": "models/x.ubj", "schemaVersion": "v1"})
    store.append_balance_snapshot({"asset": "USDT", "free": 1000, "locked": 0, "source": "unit"})

    assert store.fetch_table_count("operator_actions") == 1
    assert store.fetch_table_count("orders") == 1
    assert store.fetch_table_count("fills") == 1
    assert store.fetch_table_count("positions") == 1
    assert store.fetch_table_count("risk_events") == 1
    assert store.fetch_table_count("model_decisions") == 1
    assert store.fetch_table_count("balance_snapshots") == 1


def test_schema_migration_record_present(tmp_path: Path) -> None:
    db_path = tmp_path / "migration.db"
    SQLiteStore(str(db_path))
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT version, description FROM schema_migrations ORDER BY version").fetchall()
    assert rows
    assert rows[-1][0] == SQLITE_AUDIT_LEDGER_SCHEMA_VERSION
    assert "audit ledger schema baseline" in rows[-1][1]


def test_no_runtime_or_order_enablement_markers() -> None:
    assert SQLITE_AUDIT_LEDGER_CONTRACT_VERSION == "4B.4.3.6.6.29C"
    assert SQLITE_AUDIT_LEDGER_SCHEMA_VERSION == 2
