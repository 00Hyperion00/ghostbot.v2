from __future__ import annotations

import shutil
from pathlib import Path

TARGETS = [
    "README_APPLY_4B436631A.txt",
    "docs/LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_4B436631A.md",
    "src/tradebot/live_micro_canary_freeze_audit_closure.py",
    "tests/test_live_micro_canary_freeze_audit_closure_4B436631A.py",
    "tools/apply_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/check_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/rollback_4B436631A_live_micro_canary_freeze_audit_closure.py",
    "tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py",
]


def main() -> int:
    root = Path.cwd().resolve()
    for rel in TARGETS:
        path = root / rel
        if path.exists():
            path.unlink()
    for rel in ("_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup"):
        shutil.rmtree(root / rel, ignore_errors=True)
    print("4B.4.3.6.6.31A rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
