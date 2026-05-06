from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/training/retrain_recovery.py",
    "src/tradebot/training/train_xgb.py",
    "src/tradebot/model_quality_gate.py",
    "src/tradebot/config.py",
    "tools/run_model_retrain_recovery_4B436624D.py",
    "tests/test_model_retrain_recovery_4B436624D.py",
    "docs/MODEL_RETRAIN_RECOVERY_RUNBOOK_4B436624D.md",
]

TOKENS = {
    "src/tradebot/training/retrain_recovery.py": ["RETRAIN_RECOVERY_CONTRACT_VERSION", "evaluate_retrain_candidate", "select_best_retrain_candidate"],
    "src/tradebot/training/train_xgb.py": ["raw_target_distribution", "synthetic_class_padding_applied", "candidate_quality_contract_version"],
    "src/tradebot/model_quality_gate.py": ["TRAINING_SYNTHETIC_CLASS_PADDING_USED", "TRAINING_TARGET_ACTION_RATE_LOW"],
    "tools/run_model_retrain_recovery_4B436624D.py": ["REPORT_PREFIX", "--dry-run", "promotion_requires_explicit_flag"],
}


def main() -> None:
    print("4B.4.3.6.6.24D model retrain dataset expansion / candidate quality recovery patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if exists and path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)
            print(f" - {rel}_py_compile_ok: True")
    for rel, needles in TOKENS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for needle in needles:
            print(f" - {needle}_present: {needle in text}")


if __name__ == "__main__":
    main()
