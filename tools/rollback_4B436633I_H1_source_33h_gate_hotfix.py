from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633I_H1"
NEW_FILES = [
    "README_APPLY_4B436633I_H1.txt",
    "docs/RECOVERY_CLOSURE_REPORT_SOURCE_33H_GATE_HOTFIX_4B436633I_H1.md",
    "tests/test_recovery_closure_report_h1_4B436633I_H1.py",
    "tools/check_4B436633I_H1_source_33h_gate_hotfix.py",
    "tools/run_4B436633I_H1_source_33h_gate_hotfix.py",
    "tools/rollback_4B436633I_H1_source_33h_gate_hotfix.py",
]
MODIFIED_FILES = ["src/tradebot/recovery_closure_report.py"]


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), reverse=True)
    backup_root = backups[0] if backups else None
    restored: list[str] = []
    removed: list[str] = []
    if backup_root:
        for rel in MODIFIED_FILES:
            source = backup_root / rel
            target = root / rel
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored.append(rel)
    for rel in NEW_FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "rollback_performed": True, "backup_root": str(backup_root or ""), "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
