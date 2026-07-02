from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633F"
WRITTEN_FILES = [
    "README_APPLY_4B436633F.txt",
    "docs/EVIDENCE_RETENTION_ARCHIVE_POLICY_4B436633F.md",
    "src/tradebot/evidence_retention_archive_policy.py",
    "tests/test_evidence_retention_archive_policy_4B436633F.py",
    "tools/check_4B436633F_evidence_retention_archive_policy.py",
    "tools/run_4B436633F_evidence_retention_archive_policy.py",
]


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*")) if (root / "tools").exists() else []
    restored: list[str] = []
    removed: list[str] = []
    if backups:
        backup_root = backups[-1]
        for source in backup_root.rglob("*"):
            if source.is_file():
                relative = source.relative_to(backup_root)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored.append(relative.as_posix())
    for relative in WRITTEN_FILES:
        path = root / relative
        if path.exists() and relative not in restored:
            path.unlink()
            removed.append(relative)
    result = {
        "rolled_back": True,
        "patch_id": PATCH_ID,
        "restored_files": restored,
        "removed_files": removed,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activated": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
