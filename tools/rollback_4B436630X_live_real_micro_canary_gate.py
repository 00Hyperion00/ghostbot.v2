from __future__ import annotations

import shutil
from pathlib import Path

TARGETS = [
    "README_APPLY_4B436630X.txt",
    "docs/FIRST_LIVE_REAL_MICRO_CANARY_4B436630X.md",
    "src/tradebot/live_real_micro_canary_gate.py",
    "tests/test_live_real_micro_canary_gate_4B436630X.py",
    "tools/apply_4B436630X_live_real_micro_canary_gate.py",
    "tools/check_4B436630X_live_real_micro_canary_gate.py",
    "tools/rollback_4B436630X_live_real_micro_canary_gate.py",
    "tools/run_4B436630X_live_real_micro_canary_gate.py",
]


def main() -> int:
    root = Path.cwd().resolve()
    for rel in TARGETS:
        path = root / rel
        if path.exists():
            path.unlink()
    for rel in ("_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"):
        shutil.rmtree(root / rel, ignore_errors=True)
    print("4B.4.3.6.6.30X first live-real micro canary gate rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
