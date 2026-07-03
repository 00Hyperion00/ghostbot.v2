from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436635G"

TARGETS = [
    "README_APPLY_4B436635G.txt",
    "docs/DRY_RUN_COLLECTOR_CLOSURE_4B436635G.md",
    "src/tradebot/dry_run_collector_closure.py",
    "tests/test_dry_run_collector_closure_4B436635G.py",
    "tools/check_4B436635G_dry_run_collector_closure.py",
    "tools/run_4B436635G_dry_run_collector_closure.py",
    "tools/rollback_4B436635G_dry_run_collector_closure.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436635G")
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd()
    restored: list[str] = []
    missing: list[str] = []
    for rel in TARGETS:
        src = args.backup_root / rel
        dst = repo / rel
        if not src.exists():
            missing.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restored.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "missing_backup_files": missing}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
