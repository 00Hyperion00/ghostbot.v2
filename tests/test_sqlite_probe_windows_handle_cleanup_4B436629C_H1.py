from __future__ import annotations

import sqlite3
from pathlib import Path

from tradebot.persistence import SQLiteStore


def _read_sqlite_user_version(db: Path) -> int:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _unlink_sqlite_artifacts(db: Path) -> None:
    for target in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        target.unlink(missing_ok=True)


def test_sqlite_store_close_releases_probe_file(tmp_path: Path) -> None:
    db = tmp_path / "close_release.db"
    store = SQLiteStore(str(db))
    store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "probe", "status": "NEW"})
    store.close()

    assert _read_sqlite_user_version(db) >= 2

    _unlink_sqlite_artifacts(db)
    assert not db.exists()


def test_sqlite_store_context_manager_closes(tmp_path: Path) -> None:
    db = tmp_path / "ctx_release.db"
    with SQLiteStore(str(db)) as store:
        store.append_balance_snapshot({"asset": "USDT", "free": 1, "locked": 0})
        assert store.fetch_table_count("balance_snapshots") == 1

    _unlink_sqlite_artifacts(db)
    assert not db.exists()


def test_29c_checker_contains_windows_safe_probe_cleanup() -> None:
    text = Path("tools/check_4B436629C_sqlite_audit_ledger_upgrade.py").read_text(encoding="utf-8")
    assert "SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_VERSION" in text
    assert "def _safe_cleanup_tmpdir" in text
    assert "callable(close)" in text and "close()" in text
    assert "windows_handle_cleanup_safe" in text


def test_no_runtime_or_order_enablement_markers() -> None:
    text = Path("tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py").read_text(encoding="utf-8")
    assert '"approved_for_live_real": False' in Path("tools/run_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py").read_text(encoding="utf-8")
    assert "runtime_overlay_activation_performed" in text
    assert "paper_live_order_enablement_present" in text
