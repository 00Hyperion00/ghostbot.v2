from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436635F"
TARGETS = [
    "README_APPLY_4B436635F.txt",
    "docs/PUBLIC_DATA_COLLECTION_DRY_RUN_4B436635F.md",
    "src/tradebot/public_data_collection_dry_run.py",
    "tests/test_public_data_collection_dry_run_4B436635F.py",
    "tools/check_4B436635F_public_data_collection_dry_run.py",
    "tools/run_4B436635F_public_data_collection_dry_run.py",
    "tools/rollback_4B436635F_public_data_collection_dry_run.py",
]


def main() -> int:
    repo = Path.cwd()
    backups = sorted((repo / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))
    if not backups:
        print(json.dumps({"rolled_back": False, "reason": "backup_missing", "patch_id": PATCH_ID}, sort_keys=True))
        return 1
    backup = backups[-1]
    restored: list[str] = []
    for rel in TARGETS:
        src = backup / rel
        dst = repo / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(rel)
    print(json.dumps({"rolled_back": True, "backup_root": str(backup), "restored_files": restored, "patch_id": PATCH_ID}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
