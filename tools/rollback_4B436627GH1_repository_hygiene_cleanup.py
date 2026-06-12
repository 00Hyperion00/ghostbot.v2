from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1"
BACKUP_DIRNAME = "_patch_backup_4B436627GH1"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backup_dir = root / "tools" / BACKUP_DIRNAME
    backup_gitignore_path = backup_dir / "gitignore.before.txt"
    manifest_path = backup_dir / "tracked_paths_before.json"
    gitignore_path = root / ".gitignore"

    if not backup_gitignore_path.exists() or not manifest_path.exists():
        raise RuntimeError("ROLLBACK_BACKUP_NOT_FOUND")

    original_gitignore = backup_gitignore_path.read_text(encoding="utf-8")
    gitignore_path.write_text(original_gitignore, encoding="utf-8")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tracked_paths = [str(path) for path in manifest.get("tracked_paths_before", [])]
    restaged = 0
    for path in tracked_paths:
        if (root / path).exists():
            _git(root, "add", "-f", "--", path)
            restaged += 1

    print(f"{CONTRACT_VERSION} repository hygiene hotfix rollback completed")
    print(" - local_files_deleted: False")
    print(f" - previously_tracked_paths_restaged: {restaged}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
