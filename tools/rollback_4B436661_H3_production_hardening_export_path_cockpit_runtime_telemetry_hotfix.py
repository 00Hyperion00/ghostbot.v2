
from __future__ import annotations

import argparse
import json
from pathlib import Path

PATCH_ID = "4B436661_H3"


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436661_H3 from backup files")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    backup_dir = root / ".patch_backup" / PATCH_ID
    restored: list[str] = []
    if backup_dir.exists():
        for backup in backup_dir.glob("*.before_4B436661_H3"):
            rel = backup.name.replace(".before_4B436661_H3", "").replace("__", "/")
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            restored.append(rel)
    report = {
        "ok": True,
        "patch_id": PATCH_ID,
        "rollback_performed": bool(restored),
        "restored_files": restored,
        "paper_submit_enabled_by_patch": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(report, sort_keys=True) if args.once_json else json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
