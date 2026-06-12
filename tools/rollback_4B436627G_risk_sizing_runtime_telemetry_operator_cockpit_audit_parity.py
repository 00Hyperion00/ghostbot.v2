from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP = PROJECT_ROOT / "tools" / "_patch_backup_4B436627G"
CREATED_MARKER = BACKUP / ".created_files.txt"


def main() -> int:
    if not BACKUP.exists():
        print("4B436627G rollback skipped: backup directory not found")
        return 0
    restored = 0
    for source in sorted(path for path in BACKUP.rglob("*") if path.is_file() and path != CREATED_MARKER):
        relative = source.relative_to(BACKUP)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    removed = 0
    if CREATED_MARKER.exists():
        for item in CREATED_MARKER.read_text(encoding="utf-8").splitlines():
            if item.strip():
                target = PROJECT_ROOT / item.strip()
                if target.exists():
                    target.unlink()
                    removed += 1
    print("4B.4.3.6.6.27G rollback completed")
    print(f" - restored_files: {restored}")
    print(f" - removed_created_files: {removed}")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
