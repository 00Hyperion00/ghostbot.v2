from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
TARGET_RUNNER = TOOLS_DIR / "run_hyp005_shadow_observation_logger_4B436625V.py"
LEGACY_RUNNER = TOOLS_DIR / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"


def main() -> int:
    if not LEGACY_RUNNER.exists():
        print(f"stable_identity_rollback_error: legacy runner backup missing: {LEGACY_RUNNER}")
        return 2
    shutil.copy2(LEGACY_RUNNER, TARGET_RUNNER)
    print("4B.4.3.6.6.25V-H1 stable identity wrapper rolled back")
    print(" - scheduler_mutation_performed: False")
    print(" - config_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
