from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634A"
PATCH_FILES = [
    "README_APPLY_4B436634A.txt",
    "docs/POST_RECOVERY_NEXT_PHASE_PLANNING_4B436634A.md",
    "src/tradebot/post_recovery_next_phase_planning.py",
    "tests/test_post_recovery_next_phase_planning_4B436634A.py",
    "tools/check_4B436634A_post_recovery_next_phase_planning.py",
    "tools/run_4B436634A_post_recovery_next_phase_planning.py",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-root", default="")
    args = parser.parse_args()
    repo = Path.cwd()
    restored: list[str] = []
    removed: list[str] = []
    if args.backup_root:
        backup = repo / args.backup_root
        for rel in PATCH_FILES:
            src = backup / rel
            dst = repo / rel
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(rel)
    for rel in PATCH_FILES:
        path = repo / rel
        if path.exists() and rel not in restored:
            path.unlink()
            removed.append(rel)
    print(json.dumps({
        "patch_id": PATCH_ID,
        "restored_files": restored,
        "removed_files": removed,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "trading_action_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
    }, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
