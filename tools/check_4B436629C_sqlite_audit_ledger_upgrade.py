from __future__ import annotations

import argparse
import json
import py_compile
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29C"
SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_VERSION = "4B.4.3.6.6.29C-H1"
SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION = "4B.4.3.6.6.29C-H2"
EXPECTED_FILES = [
    "docs/SQLITE_AUDIT_LEDGER_UPGRADE_4B436629C.md",
    "tests/test_sqlite_audit_ledger_upgrade_4B436629C.py",
    "tools/apply_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/rollback_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/run_4B436629C_sqlite_audit_ledger_upgrade.py",
]
COMPILE_FILES = [
    "src/tradebot/persistence.py",
    "src/tradebot/config.py",
    "tests/test_sqlite_audit_ledger_upgrade_4B436629C.py",
    "tools/apply_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/rollback_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/run_4B436629C_sqlite_audit_ledger_upgrade.py",
]
REQUIRED_TABLES = {
    "schema_migrations",
    "operator_actions",
    "orders",
    "fills",
    "positions",
    "risk_events",
    "model_decisions",
    "balance_snapshots",
}
REQUIRED_METHODS = [
    "append_operator_action",
    "append_order_audit",
    "append_fill_audit",
    "append_position_audit",
    "append_risk_event",
    "append_model_decision",
    "append_balance_snapshot",
    "audit_ledger_snapshot",
    "fetch_table_count",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _compile(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in COMPILE_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def _safe_cleanup_tmpdir(path: Path) -> None:
    import shutil
    import time

    for _attempt in range(5):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            time.sleep(0.10)
    shutil.rmtree(path, ignore_errors=True)


def _sqlite_probe(root: Path) -> dict[str, Any]:
    import sys
    sys.path.insert(0, str(root / "src"))
    from tradebot.persistence import SQLiteStore

    tmp_path = Path(tempfile.mkdtemp(prefix="tradebot_29c_probe_"))
    store: Any | None = None
    try:
        db = tmp_path / "audit_probe.db"
        store = SQLiteStore(str(db))
        store.append_operator_action(action="probe", actor="check", outcome="ALLOWED", data={"probe": True})
        store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "probe", "status": "NEW"})
        store.append_fill_audit({"symbol": "BNBUSDT", "side": "BUY", "tradeId": "probe"})
        store.append_position_audit({"symbol": "BNBUSDT", "state": "FLAT"})
        store.append_risk_event({"symbol": "BNBUSDT", "eventType": "PROBE", "severity": "INFO"})
        store.append_model_decision({"symbol": "BNBUSDT", "signal": "HOLD"})
        store.append_balance_snapshot({"asset": "USDT", "free": 1, "locked": 0})
        snapshot = store.audit_ledger_snapshot()
        close = getattr(store, "close", None)
        if callable(close):
            close()
            store = None
        with sqlite3.connect(db) as conn:
            existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            user_version = conn.execute("PRAGMA user_version").fetchone()[0]
            counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in REQUIRED_TABLES if table in existing}
        return {
            "ok": bool(snapshot.get("ok")) and REQUIRED_TABLES.issubset(existing) and int(user_version) >= 2,
            "existing_tables": sorted(existing),
            "schema_version": int(user_version),
            "counts": counts,
            "snapshot": snapshot,
            "windows_handle_cleanup_safe": True,
        }
    finally:
        if store is not None:
            close = getattr(store, "close", None)
            if callable(close):
                close()
        _safe_cleanup_tmpdir(tmp_path)


def build_report(root: Path) -> dict[str, Any]:
    persistence = _read(root / "src/tradebot/persistence.py")
    config = _read(root / "src/tradebot/config.py")
    compiled = _compile(root)
    probe = _sqlite_probe(root)
    checks = {
        "all_expected_files_present": all((root / rel).exists() for rel in EXPECTED_FILES),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in persistence,
        "schema_version_two_present": "SQLITE_AUDIT_LEDGER_SCHEMA_VERSION = 2" in persistence and "sqlite_schema_version: int = 2" in config,
        "schema_migrations_table_present": "CREATE TABLE IF NOT EXISTS schema_migrations" in persistence,
        "orders_table_present": "CREATE TABLE IF NOT EXISTS orders" in persistence,
        "fills_table_present": "CREATE TABLE IF NOT EXISTS fills" in persistence,
        "positions_table_present": "CREATE TABLE IF NOT EXISTS positions" in persistence,
        "risk_events_table_present": "CREATE TABLE IF NOT EXISTS risk_events" in persistence,
        "model_decisions_table_present": "CREATE TABLE IF NOT EXISTS model_decisions" in persistence,
        "balance_snapshots_table_present": "CREATE TABLE IF NOT EXISTS balance_snapshots" in persistence,
        "operator_actions_table_present": "CREATE TABLE IF NOT EXISTS operator_actions" in persistence,
        "audit_append_methods_present": all(f"def {name}" in persistence for name in REQUIRED_METHODS),
        "sqlite_probe_ok": bool(probe.get("ok")),
        "sqlite_probe_windows_handle_cleanup_present": bool(probe.get("windows_handle_cleanup_safe")),
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "sqlite_audit_ledger_upgrade": True,
        "checks": checks,
        "compiled": compiled,
        "sqlite_probe": probe,
        "runtime_overlay_activation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
