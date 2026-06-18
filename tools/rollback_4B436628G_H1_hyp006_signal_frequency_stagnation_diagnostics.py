from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/run_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/apply_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/check_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/rollback_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tests/test_hyp006_signal_frequency_stagnation_diagnostics_4B436628G_H1.py",
    "docs/HYP006_R1_SIGNAL_FREQUENCY_STAGNATION_DIAGNOSTICS_4B436628G_H1.md",
    "README_APPLY_4B436628G_H1.txt",
]


def main() -> int:
    root = Path.cwd()
    removed: list[str] = []
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28G-H1 rollback completed")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    for rel in removed:
        print(f" - removed: {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
