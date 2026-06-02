from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_SHADOW_SCHEDULER_REGENERATION_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_SHADOW_SCHEDULER_PACK_READY"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "HYP005_R1_FRESH_LEDGER_NAMESPACE_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "EIGHT_SYMBOL_REFINED_SET_ENFORCED"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "TradeBot_HYP005_R1_NoOrderShadowCollection"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "Get-ScheduledTask -TaskName $BaselineTaskName"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "reports\\\\hyp005_r1"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "approved_for_paper_candidate"),
    ("src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py", "post_requests_allowed"),
    ("tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "--baseline-task-disabled"),
    ("tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "--review-ok"),
    ("tests/test_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py", "test_25ae_valid_plan_builds_isolated_r1_scheduler_pack"),
    ("docs/HYP005_R1_EIGHT_SYMBOL_SHADOW_SCHEDULER_REGENERATION_PACK_4B436625AE.md", "HYP-005-R1 Eight-Symbol No-Order Shadow Scheduler Regeneration Pack"),
    ("docs/HYP005_R1_EIGHT_SYMBOL_SHADOW_SCHEDULER_REGENERATION_PACK_4B436625AE.md", "Paper/live remain blocked"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_r1_shadow_scheduler_regeneration_pack.py",
    "tools/run_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py",
    "tests/test_hyp005_r1_shadow_scheduler_regeneration_pack_4B436625AE.py",
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
    print("4B.4.3.6.6.25AE HYP-005-R1 eight-symbol no-order shadow scheduler regeneration pack patch applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
