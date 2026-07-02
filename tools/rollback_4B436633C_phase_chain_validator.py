from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633C"
FILES = ['src/tradebot/phase_chain_validator.py', 'tools/run_4B436633C_phase_chain_validator.py', 'tools/check_4B436633C_phase_chain_validator.py', 'tests/test_phase_chain_validator_4B436633C.py', 'docs/PHASE_CHAIN_VALIDATOR_4B436633C.md', 'README_APPLY_4B436633C.txt']


def main() -> int:
    root = Path.cwd()
    backup_root = root / "tools" / f"_patch_backup_{PATCH_ID}"
    restored: list[str] = []
    removed: list[str] = []

    for rel in FILES:
        target = root / rel
        backup = backup_root / rel
        if backup.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(rel)
        elif target.exists():
            target.unlink()
            removed.append(rel)

    result = {
        "rolled_back": True,
        "patch_id": PATCH_ID,
        "restored_files": restored,
        "removed_files": removed,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
