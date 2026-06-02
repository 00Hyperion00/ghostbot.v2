from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "4B.4.3.6.6.25AE-H4"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "validate_optional_acceptance_reports"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_SHADOW_ACCEPTANCE_REPORT_OPTIONAL_FOR_COLLECTION_BOOTSTRAP"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_SHADOW_ACCEPTANCE_NOT_REQUIRED_FOR_25X_COLLECTION_READY"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "acceptance_report_required_for_collection_ready"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "previous_acceptance_informational_only"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_SHADOW_COLLECTION_IN_PROGRESS"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_SHADOW_COLLECTION_TARGET_MET"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "previous acceptance metadata is informational only"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "acceptance_report_required_for_collection_ready"),
    ("tests/test_hyp005_r1_collection_acceptance_dag_bootstrap_hotfix_25AEH4.py", "test_25aeh4_strict_dag_runs_25x_then_25w_then_25y_without_cycle_dependency"),
    ("tests/test_hyp005_r1_collection_acceptance_dag_bootstrap_hotfix_25AEH4.py", "test_25aeh4_strict_25x_cli_bootstraps_without_previous_25w_and_writes_top_level_counts"),
    ("docs/HYP005_R1_COLLECTION_ACCEPTANCE_DAG_BOOTSTRAP_HOTFIX_25AEH4.md", "Collection / Acceptance DAG Bootstrap and 25X Readiness Semantics Hotfix"),
    ("docs/HYP005_R1_COLLECTION_ACCEPTANCE_DAG_BOOTSTRAP_HOTFIX_25AEH4.md", "Paper/live/order/training/reload remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_shadow_collection_orchestrator.py",
    "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
    "tests/test_hyp005_r1_collection_acceptance_dag_bootstrap_hotfix_25AEH4.py",
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
        safe = marker.replace(" ", "_").replace("/", "_").replace("\\", "_")
        results.append((f"{safe}_present", present))
    print("4B.4.3.6.6.25AE-H4 HYP-005-R1 collection / acceptance DAG bootstrap and 25X readiness semantics hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
