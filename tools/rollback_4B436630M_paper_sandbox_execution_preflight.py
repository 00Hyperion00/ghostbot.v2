
from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "README_APPLY_4B436630M.txt",
    "docs/PAPER_SANDBOX_EXECUTION_PREFLIGHT_4B436630M.md",
    "src/tradebot/paper_sandbox_execution_preflight.py",
    "tests/test_paper_sandbox_execution_preflight_4B436630M.py",
    "tools/apply_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/check_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/rollback_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/run_4B436630M_paper_sandbox_execution_preflight.py",
]


def main() -> int:
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = Path(rel)
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    print(json.dumps({"ok": all(removed.values()), "removed": removed}, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
