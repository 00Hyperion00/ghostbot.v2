from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635B"
PATCH_VERSION = "4B.4.3.6.6.35B"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README_APPLY_4B436635B.txt",
    "docs/RUNTIME_READINESS_EVIDENCE_EXPANSION_4B436635B.md",
    "src/tradebot/runtime_readiness_evidence_expansion.py",
    "tests/test_runtime_readiness_evidence_expansion_4B436635B.py",
    "tools/check_4B436635B_runtime_readiness_evidence_expansion.py",
    "tools/run_4B436635B_runtime_readiness_evidence_expansion.py",
    "tools/rollback_4B436635B_runtime_readiness_evidence_expansion.py",
]


def main() -> int:
    removed: list[str] = []
    for item in FILES:
        path = ROOT / item
        if path.exists():
            path.unlink()
            removed.append(item)
    result: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "rolled_back": True,
        "removed_files": removed,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
