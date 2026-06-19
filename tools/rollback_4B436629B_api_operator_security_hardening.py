from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    backups = sorted((root / "tools").glob("_patch_backup_4B436629B_*"))
    if not backups:
        print("No 4B436629B backup found")
        return 1
    backup = backups[-1]
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for rel in [
        "tests/test_api_operator_security_hardening_4B436629B.py",
        "tools/check_4B436629B_api_operator_security_hardening.py",
        "tools/run_4B436629B_api_operator_security_hardening.py",
        "tools/rollback_4B436629B_api_operator_security_hardening.py",
        "docs/API_OPERATOR_SECURITY_HARDENING_4B436629B.md",
        "README_APPLY_4B436629B.txt",
    ]:
        path = root / rel
        if path.exists():
            path.unlink()
    print(f"Rolled back 4B436629B from {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
