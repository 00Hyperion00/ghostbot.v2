from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "4B.4.3.6.6.25AE-H3"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_RUNTIME_PATH_JOIN_SAFETY_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_CANONICAL_BRANCH_COMPATIBILITY_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_STRICT_EXPLICIT_REPORT_CHAINING_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", 'Join-Path $R1ReportsDir "4B436625V_hyp005_shadow_observation_logger_*.json"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", 'Join-Path $R1ReportsDir "4B436625X_hyp005_shadow_merged_ledger_*.json"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '"branch_name": "liquidity_sweep_reversal_vol_compression"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '"refined_branch_id": EXPECTED_REFINED_BRANCH_ID'),
    ("tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "--strict-explicit-chain"),
    ("tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "--collection-report-json"),
    ("tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "--strict-explicit-chain"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "--strict-explicit-chain"),
    ("tests/test_hyp005_r1_runtime_chain_path_branch_explicit_hotfix_25AEH3.py", "test_25aeh3_empty_ledger_pipeline_is_scoped_unicode_safe_and_emits_all_block_reports"),
    ("docs/HYP005_R1_RUNTIME_CHAIN_PATH_BRANCH_EXPLICIT_HOTFIX_25AEH3.md", "Runtime Chain Path Safety / Branch Compatibility / Explicit Chaining Hotfix"),
    ("docs/HYP005_R1_RUNTIME_CHAIN_PATH_BRANCH_EXPLICIT_HOTFIX_25AEH3.md", "Paper/live/order/training/reload remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py",
    "tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py",
    "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
    "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py",
    "tools/run_hyp005_shadow_operator_runbook_4B436625Y.py",
    "tests/test_hyp005_r1_runtime_chain_path_branch_explicit_hotfix_25AEH3.py",
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
    print("4B.4.3.6.6.25AE-H3 HYP-005-R1 runtime chain path safety / branch compatibility / explicit chaining hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
