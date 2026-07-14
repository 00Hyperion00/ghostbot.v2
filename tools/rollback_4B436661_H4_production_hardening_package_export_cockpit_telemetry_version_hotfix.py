from __future__ import annotations

import argparse
import json
from pathlib import Path

PATCH_ID = '4B436661_H4'


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436661_H4 patched files from .patch_backup when available")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    backup_dir = root / ".patch_backup" / PATCH_ID
    restored: list[str] = []
    if backup_dir.exists():
        for backup in sorted(backup_dir.glob("*.before_" + PATCH_ID)):
            rel = backup.name[: -len(".before_" + PATCH_ID)].replace("__", "/")
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(backup.read_bytes())
            restored.append(rel)
    report = {"ok": True, "patch_id": PATCH_ID, "rollback_performed": bool(restored), "restored_files": restored, "paper_submit_enabled_by_patch": False, "paper_submit_performed": False, "network_order_submit_performed": False, "network_request_performed": False, "approved_for_live_real": False, "exchange_submit_performed": False, "private_api_access_allowed": False, "runtime_start_performed": False, "training_performed": False, "reload_performed": False}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
