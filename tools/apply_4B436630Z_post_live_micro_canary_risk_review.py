from __future__ import annotations

import shutil
from pathlib import Path

CONTRACT = "4B.4.3.6.6.30Z"
PAYLOAD_ROOT = Path("_patch_payload") / CONTRACT
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
    payload = root / PAYLOAD_ROOT
    if not payload.exists():
        payload = root
    backup_root = root / "_patch_backup" / CONTRACT
    copied: list[str] = []
    for rel in TARGETS:
        src = payload / rel
        dst = root / rel
        if not src.exists():
            raise FileNotFoundError(f"payload file missing: {src}")
        if dst.exists():
            backup = backup_root / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    print("4B.4.3.6.6.30Z post live micro-canary risk review applied")
    print(" - copied_files:", len(copied))
    print(" - exchange_submit_performed: False")
    print(" - network_submit_attempted: False")
    print(" - additional_live_order_approved: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
