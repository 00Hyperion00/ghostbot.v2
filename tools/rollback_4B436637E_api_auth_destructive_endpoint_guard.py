from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436637E"
PATCH_VERSION = "4B.4.3.6.6.37E"
PATCH_NAME = "API Auth Destructive Endpoint Guard"
PATCH_FILES = [
    "README_APPLY_4B436637E.txt",
    "docs/API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD_4B436637E.md",
    "src/tradebot/api_auth_destructive_endpoint_guard.py",
    "tests/test_api_auth_destructive_endpoint_guard_4B436637E.py",
    "tools/check_4B436637E_api_auth_destructive_endpoint_guard.py",
    "tools/run_4B436637E_api_auth_destructive_endpoint_guard.py",
    "tools/rollback_4B436637E_api_auth_destructive_endpoint_guard.py",
]


def main() -> int:
    repo_root = Path.cwd()
    candidates = [str(repo_root / rel) for rel in PATCH_FILES]
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "rollback_available": True,
        "rollback_files": candidates,
        "rollback_performed": False,
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "note": "Rollback is intentionally manifest-only. Use git checkout/reset after operator review.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
