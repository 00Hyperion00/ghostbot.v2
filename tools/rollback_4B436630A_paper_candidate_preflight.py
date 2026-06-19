from __future__ import annotations

import argparse, shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B.4.3.6.6.30A from a selected backup directory")
    parser.add_argument("backup_dir")
    args = parser.parse_args()
    root = Path.cwd()
    backup = Path(args.backup_dir)
    if not backup.exists():
        raise SystemExit(f"Backup directory does not exist: {backup}")
    for path in backup.rglob("*"):
        if path.is_file():
            rel = path.relative_to(backup)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)
    print(f"Rollback restored files from {backup}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
