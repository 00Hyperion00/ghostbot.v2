from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = PROJECT_ROOT / "tools" / "_patch_backup_4B436627A"
ROUTER_TARGET = PROJECT_ROOT / "src" / "tradebot" / "binance_environment.py"


def main() -> int:
    if not BACKUP_DIR.exists():
        print(f"4B436627A_rollback_error: backup directory missing: {BACKUP_DIR}")
        return 2
    restored = 0
    for source in sorted(
        path for path in BACKUP_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(BACKUP_DIR)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1
    router_backup = BACKUP_DIR / "src" / "tradebot" / "binance_environment.py"
    if not router_backup.exists() and ROUTER_TARGET.exists():
        ROUTER_TARGET.unlink()
    print("4B.4.3.6.6.27A Binance REST / WebSocket environment consistency router rolled back")
    print(f" - restored_files: {restored}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
