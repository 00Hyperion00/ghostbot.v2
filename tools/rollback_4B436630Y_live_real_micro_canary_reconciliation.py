from __future__ import annotations

import shutil
from pathlib import Path

TARGETS = [
    "README_APPLY_4B436630Y.txt",
    "docs/LIVE_REAL_MICRO_CANARY_RECONCILIATION_4B436630Y.md",
    "src/tradebot/live_real_micro_canary_reconciliation.py",
    "tests/test_live_real_micro_canary_reconciliation_4B436630Y.py",
    "tools/apply_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/check_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/rollback_4B436630Y_live_real_micro_canary_reconciliation.py",
    "tools/run_4B436630Y_live_real_micro_canary_reconciliation.py",
]


def main() -> int:
    root = Path.cwd().resolve()
    for rel in TARGETS:
        path = root / rel
        if path.exists():
            path.unlink()
    for rel in ("_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"):
        shutil.rmtree(root / rel, ignore_errors=True)
    print("4B.4.3.6.6.30Y live-real micro canary reconciliation rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
