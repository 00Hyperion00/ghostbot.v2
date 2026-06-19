from __future__ import annotations

import json
import py_compile
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29C-H1"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.29C"

CHECK_PATH = Path("tools/check_4B436629C_sqlite_audit_ledger_upgrade.py")
PERSISTENCE_PATH = Path("src/tradebot/persistence.py")

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
    *EXPECTED_FILES[1:],
]

SAFE_SQLITE_PROBE = r'''def _safe_cleanup_tmpdir(path: Path) -> None:
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
'''


def _backup(path: Path, backup_dir: Path) -> None:
    if path.exists():
        target = backup_dir / path.relative_to(Path.cwd()).as_posix()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _patch_persistence_close(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "def close(self) -> None:" in text and "SQLITE_STORE_EXPLICIT_CLOSE_HOTFIX_VERSION" in text:
        return False
    changed = False
    if "SQLITE_STORE_EXPLICIT_CLOSE_HOTFIX_VERSION" not in text:
        anchor = 'SQLITE_AUDIT_LEDGER_UPGRADE_ENABLED = True\n'
        if anchor in text:
            text = text.replace(anchor, anchor + f'SQLITE_STORE_EXPLICIT_CLOSE_HOTFIX_VERSION = "{CONTRACT_VERSION}"\n')
            changed = True
    if "def close(self) -> None:" not in text:
        marker = "    def fetch_audit_events(\n"
        close_block = '''    def close(self) -> None:\n        """Close the SQLite handle so Windows can release WAL/temp probe files."""\n        with self._lock:\n            try:\n                self._conn.commit()\n            finally:\n                self._conn.close()\n\n    def __enter__(self) -> "SQLiteStore":\n        return self\n\n    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:\n        self.close()\n\n'''
        if marker not in text:
            raise RuntimeError("fetch_audit_events marker not found in persistence.py")
        text = text.replace(marker, close_block + marker)
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8", newline="\n")
    return changed


def _patch_29c_checker(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False
    if "SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_VERSION" not in text:
        text = text.replace(
            f'CONTRACT_VERSION = "{BASE_CONTRACT_VERSION}"\n',
            f'CONTRACT_VERSION = "{BASE_CONTRACT_VERSION}"\nSQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_VERSION = "{CONTRACT_VERSION}"\n',
        )
        changed = True
    if "def _safe_cleanup_tmpdir(path: Path) -> None:" not in text:
        pattern = r"def _sqlite_probe\(root: Path\) -> dict\[str, Any\]:\n.*?\n\ndef build_report\(root: Path\) -> dict\[str, Any\]:"
        replacement = SAFE_SQLITE_PROBE + "\n\ndef build_report(root: Path) -> dict[str, Any]:"
        new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
        if count != 1:
            raise RuntimeError("_sqlite_probe block not found in 29C checker")
        text = new_text
        changed = True
    if '"sqlite_probe_windows_handle_cleanup_present"' not in text:
        needle = '        "sqlite_probe_ok": bool(probe.get("ok")),\n'
        if needle not in text:
            raise RuntimeError("sqlite_probe_ok check marker not found")
        text = text.replace(
            needle,
            needle + '        "sqlite_probe_windows_handle_cleanup_present": bool(probe.get("windows_handle_cleanup_safe")),\n',
        )
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8", newline="\n")
    return changed


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


def _load_h1_report(root: Path) -> dict[str, Any]:
    import importlib.util
    module_path = root / "tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py"
    spec = importlib.util.spec_from_file_location("check_29c_h1", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load 29C-H1 checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_report(root)


def main() -> int:
    root = Path.cwd()
    if not PERSISTENCE_PATH.exists() or not CHECK_PATH.exists():
        raise SystemExit("29C files are missing; apply 29C patch before 29C-H1")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / "tools" / f"_patch_backup_4B436629C_H1_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for rel in (PERSISTENCE_PATH, CHECK_PATH):
        _backup(root / rel, backup_dir)
    patched_persistence = _patch_persistence_close(root / PERSISTENCE_PATH)
    patched_checker = _patch_29c_checker(root / CHECK_PATH)
    report = _load_h1_report(root)
    compiled = _compile(root)
    report["compiled"] = compiled
    report["checks"]["all_py_compile_ok"] = all(compiled.values())
    report["ok"] = all(report["checks"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} SQLite probe Windows handle cleanup hotfix applied")
    print(f" - patched_persistence_close: {patched_persistence}")
    print(f" - patched_29c_checker: {patched_checker}")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    print(" - runtime_overlay_activation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(" - paper_live_order_enablement_present: False")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
