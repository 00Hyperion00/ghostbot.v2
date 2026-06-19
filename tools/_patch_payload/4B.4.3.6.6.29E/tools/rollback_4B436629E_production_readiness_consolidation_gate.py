from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B.4.3.6.6.29E patch from a backup directory")
    parser.add_argument("backup_dir")
    args = parser.parse_args()
    root = Path.cwd()
    backup = Path(args.backup_dir)
    if not backup.exists():
        raise FileNotFoundError(backup)
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"restored {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
