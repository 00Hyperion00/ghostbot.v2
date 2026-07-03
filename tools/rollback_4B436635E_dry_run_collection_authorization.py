from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436635E"
FILES = [
    "README_APPLY_4B436635E.txt",
    "docs/DRY_RUN_COLLECTION_AUTHORIZATION_4B436635E.md",
    "src/tradebot/dry_run_collection_authorization.py",
    "tests/test_dry_run_collection_authorization_4B436635E.py",
    "tools/check_4B436635E_dry_run_collection_authorization.py",
    "tools/run_4B436635E_dry_run_collection_authorization.py",
    "tools/rollback_4B436635E_dry_run_collection_authorization.py",
]


def main() -> int:
    root = Path.cwd()
    removed: list[str] = []
    missing: list[str] = []
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
        else:
            missing.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "removed_files": removed, "missing_files": missing}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
