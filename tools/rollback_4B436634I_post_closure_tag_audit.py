from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436634I"
GENERATED_FILES = [
    "README_APPLY_4B436634I.txt",
    "docs/POST_CLOSURE_TAG_AUDIT_4B436634I.md",
    "src/tradebot/post_closure_tag_audit.py",
    "tests/test_post_closure_tag_audit_4B436634I.py",
    "tools/check_4B436634I_post_closure_tag_audit.py",
    "tools/run_4B436634I_post_closure_tag_audit.py",
    "tools/rollback_4B436634I_post_closure_tag_audit.py",
]


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), reverse=True)
    restored: list[str] = []
    removed: list[str] = []
    if backups:
        backup_root = backups[0]
        for backup_file in backup_root.rglob("*"):
            if backup_file.is_file():
                rel = backup_file.relative_to(backup_root)
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, dest)
                restored.append(str(rel).replace("\\", "/"))
    else:
        for rel_text in GENERATED_FILES:
            path = root / rel_text
            if path.exists() and path.is_file():
                path.unlink()
                removed.append(rel_text)
    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
