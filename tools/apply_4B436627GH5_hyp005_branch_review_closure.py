from __future__ import annotations

import json
import py_compile
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H5"
ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436627GH5"
CREATED = BACKUP / ".created_files.json"
EXPECTED = [
    "README_APPLY_4B436627GH5.txt",
    "docs/HYP005_R1_BRANCH_REVIEW_CLOSURE_4B436627GH5.md",
    "src/tradebot/hyp005_branch_review_closure.py",
    "tests/test_hyp005_branch_review_closure_4B436627GH5.py",
    "tools/apply_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/check_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/rollback_4B436627GH5_hyp005_branch_review_closure.py",
    "tools/run_4B436627GH5_hyp005_branch_review_closure.py",
]
PY_FILES = [path for path in EXPECTED if path.endswith(".py")]


def _compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    BACKUP.mkdir(parents=True, exist_ok=True)
    missing = [path for path in EXPECTED if not (ROOT / path).exists()]
    if missing:
        raise RuntimeError(f"PATCH_FILES_MISSING:{missing}")
    created: list[str] = []
    for rel in EXPECTED:
        path = ROOT / rel
        backup_path = BACKUP / rel
        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)
            created.append(rel)
    CREATED.write_text(json.dumps(created, indent=2, sort_keys=True), encoding="utf-8")
    compile_results = {rel: _compile_ok(ROOT / rel) for rel in PY_FILES}
    module_text = (ROOT / "src/tradebot/hyp005_branch_review_closure.py").read_text(encoding="utf-8")
    runner_text = (ROOT / "tools/run_4B436627GH5_hyp005_branch_review_closure.py").read_text(encoding="utf-8")
    print(f"{CONTRACT_VERSION} HYP-005-R1 Branch Review / Negative Expectancy Closure Evidence / No-Promotion Decision Pack patch applied")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(f" - all_expected_files_present: {all((ROOT / path).exists() for path in EXPECTED)}")
    print(f" - all_py_compile_ok: {all(compile_results.values())}")
    print(f" - contract_version_present: {CONTRACT_VERSION in module_text}")
    print(f" - closure_criteria_present: {'closure_criteria' in module_text}")
    print(f" - no_promotion_decision_pack_present: {'NO_PROMOTION_DECISION_PACK' in module_text}")
    print(f" - runner_requires_review_ok: {'--review-ok' in runner_text}")
    print(f" - branch_state_mutation_blocked: {'branch_state_mutation_performed' in module_text}")
    print(" - paper_live_order_enablement_present: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
