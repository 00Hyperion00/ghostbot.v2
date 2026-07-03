from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436634G"
FILES = [
    "README_APPLY_4B436634G.txt",
    "docs/SIGNATURE_APPROVAL_PACKAGE_4B436634G.md",
    "src/tradebot/signature_approval_package.py",
    "tests/test_signature_approval_package_4B436634G.py",
    "tools/check_4B436634G_signature_approval_package.py",
    "tools/run_4B436634G_signature_approval_package.py",
    "tools/rollback_4B436634G_signature_approval_package.py",
]


def main() -> int:
    repo_root = Path.cwd()
    removed: list[str] = []
    for rel in FILES:
        path = repo_root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "rollback_performed": True, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
