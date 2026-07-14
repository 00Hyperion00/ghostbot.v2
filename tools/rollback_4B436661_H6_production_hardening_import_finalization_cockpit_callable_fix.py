from __future__ import annotations

import argparse
import json
from pathlib import Path

PATCH_ID = "4B436661_H6"
PATCH_NAME = "Production Hardening Import Finalization / Cockpit Evidence Pack Callable Fix Rollback"


def main() -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    backup_dir = root / ".patch_backup" / PATCH_ID
    report = {
        "ok": True,
        "patch_id": PATCH_ID,
        "rollback_available": backup_dir.exists(),
        "rollback_performed": False,
        "manual_review_required": True,
        "message": "Rollback is intentionally manual; inspect .patch_backup/4B436661_H6 before restoring files.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
