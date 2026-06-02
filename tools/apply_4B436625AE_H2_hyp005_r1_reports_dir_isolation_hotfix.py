from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "4B.4.3.6.6.25AE-H2"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "DEFAULT_R1_REPORTS_SUBDIR"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_REPORTS_DIR_ISOLATION_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_RUNTIME_CHAIN_READS_ONLY_SCOPED_REPORTS_DIR"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_EXPLICIT_REPORT_CHAINING_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "R1_REPORTS_SUBDIR_NOT_ISOLATED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "project reports root is forbidden"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '--reports-dir "$R1ReportsDir"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '--logger-report-json "$($LatestLoggerReport.FullName)"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '--collection-report-json "$($LatestCollectionReport.FullName)"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", '--acceptance-report-json "$($LatestAcceptanceReport.FullName)"'),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "must be Disabled before H2 replacement"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "HYP005_R1_OPERATOR_COMMANDS_SCOPE_HOTFIX_VERSION"),
    ("tests/test_hyp005_r1_reports_dir_isolation_hotfix_25AEH2.py", "test_25aeh2_orchestrator_scope_does_not_import_root_baseline_ledger"),
    ("tests/test_hyp005_r1_reports_dir_isolation_hotfix_25AEH2.py", "test_25aeh2_generated_cycle_reads_only_isolated_r1_reports_dir"),
    ("docs/HYP005_R1_REPORTS_DIR_ISOLATION_RUNTIME_CHAIN_HOTFIX_25AEH2.md", "Reports-Dir Isolation / Fresh Ledger Runtime Chain Hotfix"),
    ("docs/HYP005_R1_REPORTS_DIR_ISOLATION_RUNTIME_CHAIN_HOTFIX_25AEH2.md", "Paper/live/order/training/reload remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py",
    "src/tradebot/research_hyp005_shadow_operator_runbook.py",
    "tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py",
    "tests/test_hyp005_r1_reports_dir_isolation_hotfix_25AEH2.py",
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
    print("4B.4.3.6.6.25AE-H2 HYP-005-R1 reports-dir isolation / fresh ledger runtime chain hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
