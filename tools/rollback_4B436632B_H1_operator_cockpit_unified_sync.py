from __future__ import annotations

import json
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.32B-H1"
BACKUP_DIR = Path("_legacy_launchers/4B.4.3.6.6.32B-H1")
LEGACY_LAUNCHERS = ["run_dashboard.bat", "start_dashboard.bat", "start_tradebot.bat"]

def main() -> int:
    root = Path.cwd().resolve()
    restored: dict[str, str] = {}
    for name in LEGACY_LAUNCHERS:
        backups = sorted((root / BACKUP_DIR).glob(f"{name}.*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            shutil.copy2(backups[0], root / name)
            restored[name] = backups[0].as_posix()
        else:
            restored[name] = "no_backup_found_redirect_left_in_place"
    print(json.dumps({"ok": True, "contract_version": CONTRACT_VERSION, "restored": restored}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
