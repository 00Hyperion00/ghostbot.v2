from __future__ import annotations

import json
from pathlib import Path

TARGETS = [
    "README_APPLY_4B436635H.txt",
    "docs/RUNTIME_READINESS_PLANNING_CLOSURE_4B436635H.md",
    "src/tradebot/runtime_readiness_planning_closure.py",
    "tests/test_runtime_readiness_planning_closure_4B436635H.py",
    "tools/check_4B436635H_runtime_readiness_planning_closure.py",
    "tools/run_4B436635H_runtime_readiness_planning_closure.py",
    "tools/rollback_4B436635H_runtime_readiness_planning_closure.py",
]


def main() -> int:
    repo = Path.cwd()
    removed: list[str] = []
    for rel in TARGETS:
        path = repo / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": "4B436635H", "rolled_back": True, "removed_files": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
