from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "src" / "tradebot" / "hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "run_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "check_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "apply_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "rollback_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tests" / "test_hyp006_candidate_spec_registration_4B436628B.py",
    ROOT / "docs" / "HYP006_R1_CANDIDATE_SPEC_REGISTRATION_4B436628B.md",
    ROOT / "README_APPLY_4B436628B.txt",
]


def main() -> int:
    removed = 0
    for path in TARGETS:
        if path.exists():
            path.unlink()
            removed += 1
    for cache in [ROOT / "src" / "tradebot" / "__pycache__", ROOT / "tools" / "__pycache__", ROOT / "tests" / "__pycache__"]:
        if cache.exists():
            shutil.rmtree(cache)
    print("4B.4.3.6.6.28B rollback completed")
    print(f" - removed_files: {removed}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
