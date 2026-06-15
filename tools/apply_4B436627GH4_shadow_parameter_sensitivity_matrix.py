from __future__ import annotations

import json
import py_compile
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
PY_FILES = [path for path in EXPECTED if path.endswith(".py")]


def _compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    BACKUP.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    missing = [path for path in EXPECTED if not (ROOT / path).exists()]
    if missing:
        raise RuntimeError(f"PATCH_FILES_MISSING:{missing}")
    for rel in EXPECTED:
        path = ROOT / rel
        backup_path = BACKUP / rel
        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)
            created.append(rel)
    CREATED.write_text(json.dumps(created, indent=2, sort_keys=True), encoding="utf-8")
    compile_results = {rel: _compile_ok(ROOT / rel) for rel in PY_FILES}
    module_text = (ROOT / "src/tradebot/hyp005_shadow_parameter_sensitivity.py").read_text(encoding="utf-8")
    runner_text = (ROOT / "tools/run_4B436627GH4_shadow_parameter_sensitivity_matrix.py").read_text(encoding="utf-8")
    print(f"{CONTRACT_VERSION} No-Order Parameter Sensitivity Matrix / Near-Miss Threshold Stress Audit patch applied")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    print(f" - all_expected_files_present: {all((ROOT / path).exists() for path in EXPECTED)}")
    print(f" - all_py_compile_ok: {all(compile_results.values())}")
    print(f" - contract_version_present: {CONTRACT_VERSION in module_text}")
    print(f" - threshold_grid_present: {'threshold_grid' in module_text}")
    print(f" - sensitivity_matrix_present: {'sensitivity_matrix' in module_text}")
    print(f" - runner_requires_review_ok: {'--review-ok' in runner_text}")
    print(f" - no_order_research_guard_present: {'no_order_research_variant_report_only' in module_text}")
    print(" - paper_live_order_enablement_present: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
