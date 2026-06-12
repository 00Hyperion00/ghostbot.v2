from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "tools" / "_patch_backup_4B436627E"
CREATED_MARKER = BACKUP_DIR / ".created_files.txt"


def main() -> int:
    restored = 0
    removed = 0
    if BACKUP_DIR.exists():
        for source in sorted(
            path for path in BACKUP_DIR.rglob("*")
            if path.is_file() and path != CREATED_MARKER and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        ):
            relative = source.relative_to(BACKUP_DIR)
            target = PROJECT_ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored += 1
    if CREATED_MARKER.exists():
        for raw in CREATED_MARKER.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            target = PROJECT_ROOT / raw
            if target.exists():
                target.unlink()
                removed += 1
    print("4B.4.3.6.6.27E AI startup/runtime reload threshold parity hardening rolled back")
    print(f" - restored_files: {restored}")
    print(f" - removed_created_files: {removed}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
