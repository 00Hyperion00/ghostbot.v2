from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "4B.4.3.6.6.29A"
CREATED_FILES = [
    "requirements.txt",
    "src/tradebot/production_hardening.py",
    "src/tradebot/api_security.py",
    "tools/apply_4B436629A_production_hardening_p0.py",
    "tools/check_4B436629A_production_hardening_p0.py",
    "tools/run_4B436629A_production_hardening_p0.py",
    "tools/rollback_4B436629A_production_hardening_p0.py",
    "tests/test_production_hardening_p0_4B436629A.py",
    "docs/PRODUCTION_HARDENING_P0_4B436629A.md",
]


def latest_backup() -> Path | None:
    backups = sorted((ROOT / "tools").glob("_patch_backup_4B436629A_*"), key=lambda p: p.name, reverse=True)
    return backups[0] if backups else None


def main() -> int:
    backup = latest_backup()
    if backup is not None:
        for source in backup.rglob("*"):
            if source.is_file():
                target = ROOT / source.relative_to(backup)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        print(f"{CONTRACT_VERSION} restored files from {backup}")
    else:
        print(f"{CONTRACT_VERSION} no backup directory found; removing created files only")
    for rel in CREATED_FILES:
        path = ROOT / rel
        if path.exists() and (backup is None or not (backup / rel).exists()):
            try:
                path.unlink()
                print(f" - removed: {rel}")
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
