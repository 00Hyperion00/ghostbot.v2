from __future__ import annotations

import json
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.32A"
FILES = [
    "src/tradebot/post_freeze_release_candidate_review.py",
    "tests/test_post_freeze_release_candidate_review_4B436632A.py",
    "tools/run_4B436632A_post_freeze_release_candidate_review.py",
    "tools/check_4B436632A_post_freeze_release_candidate_review.py",
    "tools/apply_4B436632A_post_freeze_release_candidate_review.py",
    "tools/rollback_4B436632A_post_freeze_release_candidate_review.py",
    "docs/POST_FREEZE_RELEASE_CANDIDATE_REVIEW_4B436632A.md",
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
    print(json.dumps({"ok": all(removed.values()), "contract_version": CONTRACT_VERSION, "removed": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
