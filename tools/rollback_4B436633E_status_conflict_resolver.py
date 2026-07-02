from __future__ import annotations

import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633E"
MANAGED_FILES = [
  "src/tradebot/status_conflict_resolver.py",
  "tools/check_4B436633E_status_conflict_resolver.py",
  "tools/run_4B436633E_status_conflict_resolver.py",
  "tests/test_status_conflict_resolver_4B436633E.py",
  "docs/STATUS_CONFLICT_RESOLVER_4B436633E.md",
  "README_APPLY_4B436633E.txt"
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backup_roots = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"), reverse=True)
    restored: list[str] = []
    removed: list[str] = []
    if backup_roots:
        backup_root = backup_roots[0]
        for source in backup_root.rglob("*"):
            if source.is_file():
                rel = source.relative_to(backup_root)
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored.append(rel.as_posix())
    for rel in MANAGED_FILES:
        target = root / rel
        if target.exists() and rel not in restored:
            target.unlink()
            removed.append(rel)
    print(json.dumps({"patch_id": PATCH_ID, "restored_files": restored, "removed_files": removed}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
