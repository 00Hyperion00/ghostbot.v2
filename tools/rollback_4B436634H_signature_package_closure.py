from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436634H"
FILES = [
    "README_APPLY_4B436634H.txt",
    "docs/SIGNATURE_PACKAGE_CLOSURE_4B436634H.md",
    "src/tradebot/signature_package_closure.py",
    "tests/test_signature_package_closure_4B436634H.py",
    "tools/check_4B436634H_signature_package_closure.py",
    "tools/run_4B436634H_signature_package_closure.py",
    "tools/rollback_4B436634H_signature_package_closure.py",
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
