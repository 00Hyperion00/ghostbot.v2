from __future__ import annotations

import json
from pathlib import Path

PATCH_FILES = [
    "README_APPLY_4B436637D.txt",
    "docs/STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_4B436637D.md",
    "src/tradebot/strict_config_unknown_key_fail_closed.py",
    "tests/test_strict_config_unknown_key_fail_closed_4B436637D.py",
    "tools/check_4B436637D_strict_config_unknown_key_fail_closed.py",
    "tools/run_4B436637D_strict_config_unknown_key_fail_closed.py",
    "tools/rollback_4B436637D_strict_config_unknown_key_fail_closed.py",
]


def main() -> int:
    removed: list[str] = []
    for rel in PATCH_FILES:
        path = Path(rel)
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({
        "rolled_back": True,
        "patch_id": "4B436637D",
        "removed_files": removed,
        "report_delete_performed": False,
        "archive_move_performed": False,
        "destructive_cleanup_performed": False,
        "strict_config_runtime_loader_mutation_performed": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
