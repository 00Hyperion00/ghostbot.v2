from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "README_APPLY_4B436630L_H2.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_HOTFIX_CHECKER_COMPAT_4B436630L_H2.md",
    "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/apply_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/rollback_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L_H2.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    print(json.dumps({"ok": all(removed.values()), "removed": removed}, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
