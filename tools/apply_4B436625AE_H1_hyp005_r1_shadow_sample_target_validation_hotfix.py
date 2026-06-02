from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_SHADOW_SCHEDULER_HOTFIX_VERSION"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "4B.4.3.6.6.25AE-H1"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "_coerce_int"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "_resolve_shadow_sample_target"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "refined_candidate_spec.shadow_sample_target"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_SHADOW_SAMPLE_TARGET_VALIDATION_NORMALIZED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "shadow_sample_target_validation"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "BASELINE_TASK_DISABLED_CONFIRMATION_REQUIRED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_FRESH_LEDGER_NAMESPACE_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "NO_AUTOMATIC_WINDOWS_TASK_MUTATION"),
    ("tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "--baseline-task-disabled"),
    ("tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "--review-ok"),
    ("tests/test_hyp005_r1_shadow_scheduler_regeneration_hotfix_25AEH1.py", "test_25aeh1_real_25ad_nested_target_generates_pack"),
    ("tests/test_hyp005_r1_shadow_scheduler_regeneration_hotfix_25AEH1.py", "test_25aeh1_cli_generates_pack_from_real_25ad_shape"),
    ("tests/test_hyp005_r1_shadow_scheduler_regeneration_hotfix_25AEH1.py", "test_25aeh1_accepts_report_emitted_by_actual_25ad_builder"),
    ("docs/HYP005_R1_SHADOW_SAMPLE_TARGET_VALIDATION_HOTFIX_25AEH1.md", "Shadow Sample Target Validation / Scheduler Pack Generation Hotfix"),
    ("docs/HYP005_R1_SHADOW_SAMPLE_TARGET_VALIDATION_HOTFIX_25AEH1.md", "Paper/live remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py",
    "tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py",
    "tests/test_hyp005_r1_shadow_scheduler_regeneration_hotfix_25AEH1.py",
)


def main() -> int:
    results: list[tuple[str, bool]] = []
    for rel_path in COMPILE_TARGETS:
        path = PROJECT_ROOT / rel_path
        exists = path.exists()
        results.append((f"{rel_path}_exists", exists))
        if exists:
            try:
                py_compile.compile(str(path), doraise=True)
                results.append((f"{rel_path}_py_compile_ok", True))
            except py_compile.PyCompileError:
                results.append((f"{rel_path}_py_compile_ok", False))
    for rel_path, marker in CHECKS:
        path = PROJECT_ROOT / rel_path
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        safe_marker = marker.replace(" ", "_").replace("/", "_").replace("\\", "_")
        results.append((f"{safe_marker}_present", present))
    print("4B.4.3.6.6.25AE-H1 HYP-005-R1 shadow sample target validation / scheduler pack generation hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
