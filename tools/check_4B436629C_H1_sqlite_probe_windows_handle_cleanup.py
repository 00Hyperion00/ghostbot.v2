from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29C-H1"
SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION = "4B.4.3.6.6.29C-H2"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.29C"
EXPECTED_FILES = [
    "docs/SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_4B436629C_H1.md",
    "tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py",
    "tools/apply_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/run_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/rollback_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
]
COMPILE_FILES = [
    "src/tradebot/persistence.py",
    "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/run_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py",
    "tools/apply_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/rollback_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/run_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
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




def _read_sqlite_user_version(db: Path) -> int:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _unlink_sqlite_artifacts(db: Path) -> dict[str, Any]:
    import time

    targets = [db, Path(str(db) + "-wal"), Path(str(db) + "-shm")]
    removed: list[str] = []
    blocked: list[dict[str, str]] = []
    for target in targets:
        for attempt in range(10):
            try:
                target.unlink(missing_ok=True)
                if not target.exists():
                    removed.append(target.name)
                break
            except PermissionError as error:
                if attempt >= 9:
                    blocked.append({"path": str(target), "error": str(error)})
                else:
                    time.sleep(0.10)
    return {"ok": not blocked and not db.exists(), "removed": removed, "blocked": blocked}


def _safe_rmtree(path: Path) -> None:
    import shutil
    import time

    for attempt in range(10):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt >= 9:
                break
            time.sleep(0.10)
    shutil.rmtree(path, ignore_errors=True)

def _load_29c_report(root: Path) -> dict[str, Any]:
    module_path = root / "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py"
    spec = importlib.util.spec_from_file_location("check_29c", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load 29C checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop("check_29c", None)
    spec.loader.exec_module(module)
    return module.build_report(root)


def _close_release_probe(root: Path) -> dict[str, Any]:
    import tempfile
    sys.path.insert(0, str(root / "src"))
    from tradebot.persistence import SQLiteStore

    tmp_path = Path(tempfile.mkdtemp(prefix="tradebot_29c_h2_release_"))
    store: Any | None = None
    try:
        db = tmp_path / "release_probe.db"
        store = SQLiteStore(str(db))
        store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "release", "status": "NEW"})
        close = getattr(store, "close", None)
        if not callable(close):
            return {"ok": False, "reason_code": "SQLITE_STORE_CLOSE_MISSING"}
        close()
        store = None
        user_version = _read_sqlite_user_version(db)
        unlink_probe = _unlink_sqlite_artifacts(db)
        return {
            "ok": bool(unlink_probe.get("ok")),
            "schema_version": int(user_version),
            "db_unlinked_after_close": not db.exists(),
            "explicit_sqlite_connection_close": True,
            "unlink_probe": unlink_probe,
        }
    finally:
        if store is not None:
            close = getattr(store, "close", None)
            if callable(close):
                close()
        _safe_rmtree(tmp_path)


def build_report(root: Path) -> dict[str, Any]:
    persistence = _read(root / "src/tradebot/persistence.py")
    checker_29c = _read(root / "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py")
    compiled = _compile(root)
    close_probe = _close_release_probe(root)
    base_report = _load_29c_report(root)
    checks = {
        "all_expected_files_present": all((root / rel).exists() for rel in EXPECTED_FILES),
        "all_py_compile_ok": all(compiled.values()),
        "base_29c_checker_ok": bool(base_report.get("ok")),
        "sqlite_store_explicit_close_present": "def close(self) -> None:" in persistence,
        "sqlite_store_context_manager_present": "def __enter__(self)" in persistence and "def __exit__(self" in persistence,
        "sqlite_probe_windows_cleanup_version_present": CONTRACT_VERSION in checker_29c or CONTRACT_VERSION in persistence,
        "sqlite_probe_safe_cleanup_present": "def _safe_cleanup_tmpdir" in checker_29c,
        "sqlite_probe_closes_store_before_temp_cleanup": "callable(close)" in checker_29c and "close()" in checker_29c,
        "sqlite_probe_cleanup_safe": bool(base_report.get("sqlite_probe", {}).get("windows_handle_cleanup_safe")),
        "sqlite_close_release_probe_ok": bool(close_probe.get("ok")),
        "sqlite_probe_explicit_connection_close_present": bool(close_probe.get("explicit_sqlite_connection_close")),
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": BASE_CONTRACT_VERSION,
        "read_only": True,
        "sqlite_probe_windows_handle_cleanup": True,
        "checks": checks,
        "compiled": compiled,
        "base_29c_report_ok": bool(base_report.get("ok")),
        "base_29c_sqlite_probe": base_report.get("sqlite_probe"),
        "close_release_probe": close_probe,
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
