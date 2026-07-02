from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCH_ID = "4B436633G_H1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Rollback 4B436633G-H1 from latest backup")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    backups = sorted((root / "tools").glob(f"_patch_backup_{PATCH_ID}_*"))
    restored: list[str] = []
    if backups:
        backup = backups[-1]
        source = backup / "src" / "tradebot" / "archive_execution_preflight.py"
        target = root / "src" / "tradebot" / "archive_execution_preflight.py"
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored.append("src/tradebot/archive_execution_preflight.py")
    result = {"patch_id": PATCH_ID, "rolled_back": bool(restored), "restored_files": restored}
    print(json.dumps(result, sort_keys=True) if args.once_json else json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
