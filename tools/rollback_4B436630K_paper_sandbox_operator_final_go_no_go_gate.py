from __future__ import annotations

import argparse
import json
from pathlib import Path

FILES = [
    "README_APPLY_4B436630K.txt",
    "docs/PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_4B436630K.md",
    "src/tradebot/paper_sandbox_operator_final_go_no_go_gate.py",
    "tests/test_paper_sandbox_operator_final_go_no_go_gate_4B436630K.py",
    "tools/apply_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/rollback_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/run_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    payload = {
        "ok": all(removed.values()),
        "contract_version": "4B.4.3.6.6.30K",
        "removed": removed,
        "config_fields_left_intentionally": True,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
