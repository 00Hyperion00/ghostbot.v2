from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436637F"
PATCH_VERSION = "4B.4.3.6.6.37F"
PATCH_NAME = "Typed Confirmation Destructive Actions"
PATCH_FILES = [
    "README_APPLY_4B436637F.txt",
    "docs/TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS_4B436637F.md",
    "src/tradebot/typed_confirmation_destructive_actions.py",
    "tests/test_typed_confirmation_destructive_actions_4B436637F.py",
    "tools/check_4B436637F_typed_confirmation_destructive_actions.py",
    "tools/run_4B436637F_typed_confirmation_destructive_actions.py",
    "tools/rollback_4B436637F_typed_confirmation_destructive_actions.py",
]


def main() -> int:
    repo_root = Path.cwd()
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "rollback_available": True,
        "rollback_files": [str(repo_root / rel) for rel in PATCH_FILES],
        "rollback_performed": False,
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "note": "Rollback is intentionally manifest-only. Use git checkout/reset after operator review.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
