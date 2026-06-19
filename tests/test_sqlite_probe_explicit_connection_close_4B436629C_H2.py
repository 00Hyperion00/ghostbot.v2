from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from typing import Any

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


def test_direct_sqlite_probe_uses_explicit_connection_close(tmp_path: Path) -> None:
    db = tmp_path / "h2_close_release.db"
    store = SQLiteStore(str(db))
    store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "h2", "status": "NEW"})
    store.close()

    assert _read_sqlite_user_version(db) >= 2
    _unlink_sqlite_artifacts(db)
    assert not db.exists()


def test_h1_checker_no_longer_uses_temporarydirectory_release_probe() -> None:
    text = Path("tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py").read_text(encoding="utf-8")
    assert "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION" in text
    assert "tradebot_29c_h2_release_" in text
    assert "with tempfile.TemporaryDirectory() as tmp:" not in text
    assert "def _read_sqlite_user_version(db: Path) -> int:" in text
    assert "conn.close()" in text
    assert "def _unlink_sqlite_artifacts(db: Path)" in text


def test_h1_test_no_sqlite_context_manager_leak() -> None:
    text = Path("tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py").read_text(encoding="utf-8")
    assert "with sqlite3.connect(db) as conn:" not in text
    assert "def _read_sqlite_user_version(db: Path) -> int:" in text
    assert "conn.close()" in text


def test_h2_checker_accepts_base_and_h1_reports() -> None:
    module_path = Path("tools/check_4B436629C_H2_sqlite_probe_explicit_connection_close.py")
    spec = importlib.util.spec_from_file_location("check_29c_h2_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop("check_29c_h2_test", None)
    spec.loader.exec_module(module)
    report: dict[str, Any] = module.build_report(Path.cwd())
    assert report["ok"] is True
    assert report["checks"]["base_29c_checker_ok"] is True
    assert report["checks"]["h1_checker_ok"] is True
    assert report["checks"]["direct_explicit_close_probe_ok"] is True
    assert report["trading_action_performed"] is False
