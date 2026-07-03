from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634C"
FILES = [
    "README_APPLY_4B436634C.txt",
    "docs/OPERATOR_REVIEW_GATE_4B436634C.md",
    "src/tradebot/operator_review_gate.py",
    "tests/test_operator_review_gate_4B436634C.py",
    "tools/check_4B436634C_operator_review_gate.py",
    "tools/run_4B436634C_operator_review_gate.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436634C files")
    parser.add_argument("--backup-root", default="")
    args = parser.parse_args()
    repo = Path.cwd()
    restored: list[str] = []
    removed: list[str] = []

    backup_root = repo / args.backup_root if args.backup_root else None
    for rel in FILES:
        path = repo / rel
        backup = backup_root / rel if backup_root else None
        if backup is not None and backup.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
            restored.append(rel)
        elif path.exists():
            path.unlink()
            removed.append(rel)

    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
