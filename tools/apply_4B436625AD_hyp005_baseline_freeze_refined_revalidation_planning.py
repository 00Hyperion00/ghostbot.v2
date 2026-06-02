from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "HYP005_R1_REVALIDATION_PLANNING_READY"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "BASELINE_EVIDENCE_FROZEN"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "fresh_ledger_namespace"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "starting_unique_shadow_observation_count"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "approved_for_next_scheduler_pack_patch"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "approved_for_scheduler_regeneration"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "scheduler_regeneration_requires_separate_operator_patch"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "config_mutation_performed"),
    ("src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py", "post_requests_allowed"),
    ("tools/run_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py", "--input-json"),
    ("tools/run_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py", "--review-ok"),
    ("tests/test_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py", "test_25ad_valid_refinement_freezes_baseline_and_plans_fresh_r1"),
    ("docs/HYP005_BASELINE_FREEZE_REFINED_REVALIDATION_PLANNING_GATE_4B436625AD.md", "Baseline Evidence Freeze / Refined Candidate Revalidation Planning Gate"),
    ("docs/HYP005_BASELINE_FREEZE_REFINED_REVALIDATION_PLANNING_GATE_4B436625AD.md", "Paper/live remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_baseline_freeze_refined_revalidation_planning.py",
    "tools/run_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py",
    "tests/test_hyp005_baseline_freeze_refined_revalidation_planning_4B436625AD.py",
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
        safe_marker = marker.replace(" ", "_").replace("/", "_")
        results.append((f"{safe_marker}_present", present))

    print("4B.4.3.6.6.25AD HYP-005 baseline evidence freeze / refined candidate revalidation planning gate patch applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
