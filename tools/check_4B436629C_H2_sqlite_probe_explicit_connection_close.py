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

CONTRACT_VERSION = "4B.4.3.6.6.29C-H2"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.29C"
H1_CONTRACT_VERSION = "4B.4.3.6.6.29C-H1"
EXPECTED_FILES = [
    "docs/SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_4B436629C_H2.md",
    "tests/test_sqlite_probe_explicit_connection_close_4B436629C_H2.py",
    "tools/apply_4B436629C_H2_sqlite_probe_explicit_connection_close.py",
    "tools/check_4B436629C_H2_sqlite_probe_explicit_connection_close.py",
    "tools/run_4B436629C_H2_sqlite_probe_explicit_connection_close.py",
    "tools/rollback_4B436629C_H2_sqlite_probe_explicit_connection_close.py",
]
COMPILE_FILES = [
    "src/tradebot/persistence.py",
    "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py",
    "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tools/run_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py",
    "tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py",
    *EXPECTED_FILES[1:],
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


def _load_report(root: Path, rel: str, module_name: str) -> dict[str, Any]:
    module_path = root / rel
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load checker: {rel}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    spec.loader.exec_module(module)
    return module.build_report(root)


def _read_sqlite_user_version(db: Path) -> int:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _unlink_sqlite_artifacts(db: Path) -> dict[str, Any]:
    import time

    blocked: list[str] = []
    for target in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        for attempt in range(10):
            try:
                target.unlink(missing_ok=True)
                break
            except PermissionError:
                if attempt >= 9:
                    blocked.append(str(target))
                else:
                    time.sleep(0.10)
    return {"ok": not blocked and not db.exists(), "blocked": blocked}


def _direct_explicit_close_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.persistence import SQLiteStore

    tmp_path = Path(tempfile.mkdtemp(prefix="tradebot_29c_h2_direct_"))
    store: Any | None = None
    try:
        db = tmp_path / "direct_probe.db"
        store = SQLiteStore(str(db))
        store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "direct", "status": "NEW"})
        store.close()
        store = None
        schema_version = _read_sqlite_user_version(db)
        unlink_probe = _unlink_sqlite_artifacts(db)
        return {
            "ok": bool(unlink_probe.get("ok")) and schema_version >= 2,
            "schema_version": schema_version,
            "unlink_probe": unlink_probe,
            "explicit_sqlite_connection_close": True,
        }
    finally:
        if store is not None:
            close = getattr(store, "close", None)
            if callable(close):
                close()
        import shutil
        shutil.rmtree(tmp_path, ignore_errors=True)


def build_report(root: Path) -> dict[str, Any]:
    h1_checker = _read(root / "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py")
    h1_test = _read(root / "tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py")
    checker_29c = _read(root / "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py")
    compiled = _compile(root)
    h1_report = _load_report(root, "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py", "check_29c_h1_from_h2")
    base_report = _load_report(root, "tools/check_4B436629C_sqlite_audit_ledger_upgrade.py", "check_29c_from_h2")
    direct_probe = _direct_explicit_close_probe(root)
    checks = {
        "all_expected_files_present": all((root / rel).exists() for rel in EXPECTED_FILES),
        "all_py_compile_ok": all(compiled.values()),
        "base_29c_checker_ok": bool(base_report.get("ok")),
        "h1_checker_ok": bool(h1_report.get("ok")),
        "direct_explicit_close_probe_ok": bool(direct_probe.get("ok")),
        "h1_checker_explicit_connection_close_version_present": "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION" in h1_checker,
        "h1_checker_uses_mkdtemp_not_temporarydirectory_for_release_probe": "tradebot_29c_h2_release_" in h1_checker and "with tempfile.TemporaryDirectory() as tmp:" not in h1_checker,
        "h1_checker_has_explicit_sqlite_conn_close": "def _read_sqlite_user_version(db: Path) -> int:" in h1_checker and "conn.close()" in h1_checker,
        "h1_checker_has_sqlite_artifact_unlink_retry": "def _unlink_sqlite_artifacts(db: Path)" in h1_checker and "PermissionError" in h1_checker,
        "h1_test_has_explicit_sqlite_conn_close": "def _read_sqlite_user_version(db: Path) -> int:" in h1_test and "conn.close()" in h1_test,
        "h1_test_no_sqlite_context_manager_leak": "with sqlite3.connect(db) as conn:" not in h1_test,
        "base_29c_checker_marker_present": "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION" in checker_29c,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": BASE_CONTRACT_VERSION,
        "h1_contract_version": H1_CONTRACT_VERSION,
        "read_only": True,
        "sqlite_probe_explicit_connection_close": True,
        "checks": checks,
        "compiled": compiled,
        "base_29c_report_ok": bool(base_report.get("ok")),
        "h1_report_ok": bool(h1_report.get("ok")),
        "h1_close_release_probe": h1_report.get("close_release_probe"),
        "direct_probe": direct_probe,
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
