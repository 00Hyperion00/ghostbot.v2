from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_shadow_quality_audit.py", "load_hyp005_shadow_observations_with_dedupe_stats"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "HYP005_SYMBOL_RISK_PRUNING_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "HYP005_CONTINUE_WITH_BASELINE_SYMBOLS"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "HYP005_BRANCH_REFINEMENT_REQUIRED"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "HYP005_BRANCH_CLOSURE_RECOMMENDED"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "approved_for_scheduler_regeneration"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "scheduler_regeneration_requires_separate_operator_patch"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "config_mutation_performed"),
    ("src/tradebot/research_hyp005_symbol_risk_pruning_decision.py", "post_requests_allowed"),
    ("tools/run_hyp005_symbol_risk_pruning_decision_4B436625AC.py", "--include-all"),
    ("tools/run_hyp005_symbol_risk_pruning_decision_4B436625AC.py", "--review-ok"),
    ("tests/test_hyp005_symbol_risk_pruning_decision_4B436625AC.py", "test_25ac_pruned_symbol_set_can_pass_when_avax_doge_removal_repairs_edge"),
    ("docs/HYP005_SYMBOL_RISK_PRUNING_DECISION_GATE_4B436625AC.md", "Symbol Risk Pruning / Candidate Continuation Decision Gate"),
    ("docs/HYP005_SYMBOL_RISK_PRUNING_DECISION_GATE_4B436625AC.md", "Paper/live remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_symbol_risk_pruning_decision.py",
    "tools/run_hyp005_symbol_risk_pruning_decision_4B436625AC.py",
    "tests/test_hyp005_symbol_risk_pruning_decision_4B436625AC.py",
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

    print("4B.4.3.6.6.25AC HYP-005 symbol risk pruning / candidate continuation decision gate patch applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
