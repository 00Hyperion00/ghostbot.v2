from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATED_PATHS = [
    "src/tradebot/hyp005_shadow_stagnation_diagnostics.py",
    "tools/run_4B436627GH3_shadow_stagnation_diagnostics.py",
    "tools/check_4B436627GH3_shadow_stagnation_diagnostics.py",
    "tests/test_shadow_stagnation_diagnostics_4B436627GH3.py",
    "docs/SHADOW_OBSERVATION_STAGNATION_DIAGNOSTICS_4B436627GH3.md",
    "README_APPLY_4B436627GH3.txt",
]


def main() -> int:
    deleted: list[str] = []
    for relative in CREATED_PATHS:
        path = ROOT / relative
        if path.exists():
            path.unlink()
            deleted.append(relative)
    print("4B.4.3.6.6.27G-H3 rollback completed")
    for item in deleted:
        print(f" - deleted: {item}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
