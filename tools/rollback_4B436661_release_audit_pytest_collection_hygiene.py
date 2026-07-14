from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436661"
PATCH_VERSION = "4B.4.3.6.6.61"
PATCH_NAME = "Release Audit / Repository Hygiene / Pytest Collection Isolation"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _root()
    pytest_ini = root / "pytest.ini"
    backup = root / ".patch_backup" / PATCH_ID / "pytest.ini.before_4B436661"
    restored = False
    if backup.exists():
        pytest_ini.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        restored = True
    result = {
        "ok": True,
        "rolled_back": restored,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "pytest_ini_restored_from_backup": restored,
        "pytest_ini_backup_path": str(backup) if backup.exists() else None,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
