from __future__ import annotations

import argparse
import json
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30L"
FILES = [
    "README_APPLY_4B436630L.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_4B436630L.md",
    "src/tradebot/paper_sandbox_candidate_unlock_gate.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py",
    "tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/rollback_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    result: dict[str, object] = {"contract_version": CONTRACT_VERSION, "dry_run": not args.apply, "removed": {}}
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if args.apply and path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    result["removed"] = removed
    result["ok"] = all(removed.values()) if args.apply else True
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
