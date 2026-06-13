from __future__ import annotations

import json
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H2"
ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436627GH2"
CREATED = BACKUP / ".created_files.json"


def main() -> int:
    if not BACKUP.exists():
        print(f"{CONTRACT_VERSION} rollback skipped: backup directory missing")
        return 0
    restored = 0
    for relative in (
        "tools/run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py",
        "tools/run_hyp005_shadow_observation_logger_4B436625V.py",
        "tools/run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1",
    ):
        source = BACKUP / relative
        target = ROOT / relative
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored += 1
    removed = 0
    if CREATED.exists():
        for relative in json.loads(CREATED.read_text(encoding="utf-8")):
            target = ROOT / relative
            if target.exists():
                target.unlink()
                removed += 1
    print(f"{CONTRACT_VERSION} rollback completed")
    print(f" - restored_files: {restored}")
    print(f" - removed_created_files: {removed}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
