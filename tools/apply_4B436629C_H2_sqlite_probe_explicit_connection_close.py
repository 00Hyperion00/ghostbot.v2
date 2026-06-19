from __future__ import annotations

import importlib.util
import json
import py_compile
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29C-H2"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.29C"
H1_CONTRACT_VERSION = "4B.4.3.6.6.29C-H1"

H1_CHECK_PATH = Path("tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py")
H1_TEST_PATH = Path("tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py")
CHECK_29C_PATH = Path("tools/check_4B436629C_sqlite_audit_ledger_upgrade.py")
PERSISTENCE_PATH = Path("src/tradebot/persistence.py")

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

HELPERS = '''\n\ndef _read_sqlite_user_version(db: Path) -> int:\n    conn = sqlite3.connect(db)\n    try:\n        row = conn.execute("PRAGMA user_version").fetchone()\n        return int(row[0]) if row else 0\n    finally:\n        conn.close()\n\n\ndef _unlink_sqlite_artifacts(db: Path) -> dict[str, Any]:\n    import time\n\n    targets = [db, Path(str(db) + "-wal"), Path(str(db) + "-shm")]\n    removed: list[str] = []\n    blocked: list[dict[str, str]] = []\n    for target in targets:\n        for attempt in range(10):\n            try:\n                target.unlink(missing_ok=True)\n                if not target.exists():\n                    removed.append(target.name)\n                break\n            except PermissionError as error:\n                if attempt >= 9:\n                    blocked.append({"path": str(target), "error": str(error)})\n                else:\n                    time.sleep(0.10)\n    return {"ok": not blocked and not db.exists(), "removed": removed, "blocked": blocked}\n\n\ndef _safe_rmtree(path: Path) -> None:\n    import shutil\n    import time\n\n    for attempt in range(10):\n        try:\n            shutil.rmtree(path)\n            return\n        except FileNotFoundError:\n            return\n        except PermissionError:\n            if attempt >= 9:\n                break\n            time.sleep(0.10)\n    shutil.rmtree(path, ignore_errors=True)\n'''

NEW_CLOSE_RELEASE_PROBE = '''def _close_release_probe(root: Path) -> dict[str, Any]:\n    import tempfile\n    sys.path.insert(0, str(root / "src"))\n    from tradebot.persistence import SQLiteStore\n\n    tmp_path = Path(tempfile.mkdtemp(prefix="tradebot_29c_h2_release_"))\n    store: Any | None = None\n    try:\n        db = tmp_path / "release_probe.db"\n        store = SQLiteStore(str(db))\n        store.append_order_audit({"symbol": "BNBUSDT", "side": "BUY", "orderId": "release", "status": "NEW"})\n        close = getattr(store, "close", None)\n        if not callable(close):\n            return {"ok": False, "reason_code": "SQLITE_STORE_CLOSE_MISSING"}\n        close()\n        store = None\n        user_version = _read_sqlite_user_version(db)\n        unlink_probe = _unlink_sqlite_artifacts(db)\n        return {\n            "ok": bool(unlink_probe.get("ok")),\n            "schema_version": int(user_version),\n            "db_unlinked_after_close": not db.exists(),\n            "explicit_sqlite_connection_close": True,\n            "unlink_probe": unlink_probe,\n        }\n    finally:\n        if store is not None:\n            close = getattr(store, "close", None)\n            if callable(close):\n                close()\n        _safe_rmtree(tmp_path)\n\n\n'''

TEST_HELPERS = '''\n\ndef _read_sqlite_user_version(db: Path) -> int:\n    conn = sqlite3.connect(db)\n    try:\n        row = conn.execute("PRAGMA user_version").fetchone()\n        return int(row[0]) if row else 0\n    finally:\n        conn.close()\n\n\ndef _unlink_sqlite_artifacts(db: Path) -> None:\n    for target in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):\n        target.unlink(missing_ok=True)\n'''


def _backup(path: Path, backup_dir: Path) -> None:
    if not path.exists():
        return
    target = backup_dir / path.relative_to(Path.cwd()).as_posix()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _patch_h1_checker(path: Path) -> bool:
    text = _read(path)
    if not text:
        raise RuntimeError(f"Missing H1 checker: {path}")
    changed = False
    if "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION" not in text:
        marker = f'CONTRACT_VERSION = "{H1_CONTRACT_VERSION}"\n'
        if marker not in text:
            raise RuntimeError("H1 checker contract marker not found")
        text = text.replace(marker, marker + f'SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION = "{CONTRACT_VERSION}"\n')
        changed = True
    if "def _read_sqlite_user_version(db: Path) -> int:" not in text:
        marker = "def _load_29c_report(root: Path) -> dict[str, Any]:\n"
        if marker not in text:
            raise RuntimeError("H1 checker load-report marker not found")
        text = text.replace(marker, HELPERS + "\n" + marker)
        changed = True
    pattern = r"def _close_release_probe\(root: Path\) -> dict\[str, Any\]:\n.*?\n\ndef build_report\(root: Path\) -> dict\[str, Any\]:"
    new_text, count = re.subn(pattern, NEW_CLOSE_RELEASE_PROBE + "def build_report(root: Path) -> dict[str, Any]:", text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("H1 _close_release_probe block not found")
    if new_text != text:
        text = new_text
        changed = True
    replacements = {
        '"sqlite_close_release_probe_ok": bool(close_probe.get("ok")),\n': '"sqlite_close_release_probe_ok": bool(close_probe.get("ok")),\n        "sqlite_probe_explicit_connection_close_present": bool(close_probe.get("explicit_sqlite_connection_close")),\n',
    }
    for old, new in replacements.items():
        if old in text and new not in text:
            text = text.replace(old, new)
            changed = True
    if changed:
        _write(path, text)
    return changed


def _patch_h1_test(path: Path) -> bool:
    text = _read(path)
    if not text:
        raise RuntimeError(f"Missing H1 test: {path}")
    changed = False
    if "def _read_sqlite_user_version(db: Path) -> int:" not in text:
        marker = "from tradebot.persistence import SQLiteStore\n"
        if marker not in text:
            raise RuntimeError("H1 test import marker not found")
        text = text.replace(marker, marker + TEST_HELPERS)
        changed = True
    old = '''    with sqlite3.connect(db) as conn:\n        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) >= 2\n\n    db.unlink()\n    assert not db.exists()\n'''
    new = '''    assert _read_sqlite_user_version(db) >= 2\n\n    _unlink_sqlite_artifacts(db)\n    assert not db.exists()\n'''
    if old in text:
        text = text.replace(old, new)
        changed = True
    old2 = '''    db.unlink()\n    assert not db.exists()\n'''
    new2 = '''    _unlink_sqlite_artifacts(db)\n    assert not db.exists()\n'''
    if old2 in text:
        text = text.replace(old2, new2)
        changed = True
    if changed:
        _write(path, text)
    return changed


def _patch_29c_checker_marker(path: Path) -> bool:
    text = _read(path)
    if not text:
        raise RuntimeError(f"Missing 29C checker: {path}")
    changed = False
    if "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION" not in text:
        marker = 'SQLITE_PROBE_WINDOWS_HANDLE_CLEANUP_VERSION = "4B.4.3.6.6.29C-H1"\n'
        if marker in text:
            text = text.replace(marker, marker + f'SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_VERSION = "{CONTRACT_VERSION}"\n')
            changed = True
    if changed:
        _write(path, text)
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


def _load_h2_report(root: Path) -> dict[str, Any]:
    module_path = root / "tools/check_4B436629C_H2_sqlite_probe_explicit_connection_close.py"
    spec = importlib.util.spec_from_file_location("check_29c_h2", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load 29C-H2 checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop("check_29c_h2", None)
    spec.loader.exec_module(module)
    return module.build_report(root)


def main() -> int:
    root = Path.cwd()
    missing_base = [str(path) for path in (PERSISTENCE_PATH, CHECK_29C_PATH, H1_CHECK_PATH, H1_TEST_PATH) if not path.exists()]
    if missing_base:
        raise SystemExit(f"29C/H1 files are missing; apply 29C and 29C-H1 first: {missing_base}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / "tools" / f"_patch_backup_4B436629C_H2_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for rel in (H1_CHECK_PATH, H1_TEST_PATH, CHECK_29C_PATH):
        _backup(root / rel, backup_dir)
    patched_h1_checker = _patch_h1_checker(root / H1_CHECK_PATH)
    patched_h1_test = _patch_h1_test(root / H1_TEST_PATH)
    patched_29c_checker_marker = _patch_29c_checker_marker(root / CHECK_29C_PATH)
    compiled = _compile(root)
    report = _load_h2_report(root)
    report["compiled"] = compiled
    report["checks"]["all_py_compile_ok"] = all(compiled.values())
    report["ok"] = all(report["checks"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} SQLite probe explicit connection close hotfix applied")
    print(f" - patched_h1_checker: {patched_h1_checker}")
    print(f" - patched_h1_test: {patched_h1_test}")
    print(f" - patched_29c_checker_marker: {patched_29c_checker_marker}")
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
