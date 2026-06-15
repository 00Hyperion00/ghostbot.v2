from __future__ import annotations

import json
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H4"
ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436627GH4"
CREATED = BACKUP / ".created_files.json"
EXPECTED = [
    "README_APPLY_4B436627GH4.txt",
    "docs/SHADOW_PARAMETER_SENSITIVITY_MATRIX_4B436627GH4.md",
    "src/tradebot/hyp005_shadow_parameter_sensitivity.py",
    "tests/test_shadow_parameter_sensitivity_matrix_4B436627GH4.py",
    "tools/apply_4B436627GH4_shadow_parameter_sensitivity_matrix.py",
    "tools/check_4B436627GH4_shadow_parameter_sensitivity_matrix.py",
    "tools/rollback_4B436627GH4_shadow_parameter_sensitivity_matrix.py",
    "tools/run_4B436627GH4_shadow_parameter_sensitivity_matrix.py",
]


def main() -> int:
    created = json.loads(CREATED.read_text(encoding="utf-8")) if CREATED.exists() else EXPECTED
    for rel in created:
        path = ROOT / rel
        backup = BACKUP / rel
        if backup.exists():
            shutil.copy2(backup, path)
        elif path.exists():
            path.unlink()
    print(f"{CONTRACT_VERSION} rollback completed")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
