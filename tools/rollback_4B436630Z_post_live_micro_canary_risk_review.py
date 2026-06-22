from __future__ import annotations

import shutil
from pathlib import Path

CONTRACT = "4B.4.3.6.6.30Z"
TARGETS = [
    "README_APPLY_4B436630Z.txt",
    "src/tradebot/post_live_micro_canary_risk_review.py",
    "tools/run_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/check_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/apply_4B436630Z_post_live_micro_canary_risk_review.py",
    "tools/rollback_4B436630Z_post_live_micro_canary_risk_review.py",
    "tests/test_post_live_micro_canary_risk_review_4B436630Z.py",
    "docs/POST_LIVE_MICRO_CANARY_RISK_REVIEW_4B436630Z.md",
]


def main() -> int:
    root = Path.cwd().resolve()
    backup_root = root / "_patch_backup" / CONTRACT
    for rel in TARGETS:
        dst = root / rel
        backup = backup_root / rel
        if backup.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, dst)
        elif dst.exists():
            dst.unlink()
    print("4B.4.3.6.6.30Z post live micro-canary risk review rollback completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
