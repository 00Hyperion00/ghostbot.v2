from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634D"
FILES = [
    "README_APPLY_4B436634D.txt",
    "docs/OPERATOR_DECISION_TOKEN_4B436634D.md",
    "src/tradebot/operator_decision_token.py",
    "tests/test_operator_decision_token_4B436634D.py",
    "tools/check_4B436634D_operator_decision_token.py",
    "tools/run_4B436634D_operator_decision_token.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436634D files")
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
