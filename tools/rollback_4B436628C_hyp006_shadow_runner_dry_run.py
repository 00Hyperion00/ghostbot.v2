from __future__ import annotations

import shutil
from pathlib import Path

PATCH_ID = "4B436628C"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = PROJECT_ROOT / "tools" / f"_patch_backup_{PATCH_ID}"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_runner_dry_run.py",
    "tools/run_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/check_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/apply_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/rollback_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tests/test_hyp006_shadow_runner_dry_run_4B436628C.py",
    "docs/HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_4B436628C.md",
]


def main() -> int:
    restored = []
    removed = []
    for relative in EXPECTED_FILES:
        target = PROJECT_ROOT / relative
        backup = BACKUP_ROOT / relative
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(relative)
        elif target.exists():
            target.unlink()
            removed.append(relative)
    print("4B436628C rollback complete")
    print(f" - restored: {len(restored)}")
    print(f" - removed: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
