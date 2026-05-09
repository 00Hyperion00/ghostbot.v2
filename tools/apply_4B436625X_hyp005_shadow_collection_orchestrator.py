#!/usr/bin/env python3
"""Apply/verify 4B.4.3.6.6.25X HYP-005 shadow collection orchestrator patch."""

from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "Hyp005ShadowCollectionLimits"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "ShadowCollectionPlan"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "ShadowCollectionProgress"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "merge_observations"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "NO_ORDER_COLLECTION_ONLY"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "approved_for_live_real"),
    ("src/tradebot/research_hyp005_shadow_collection_orchestrator.py", "post_requests_allowed"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "__candidate_spec_json"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "__logger_report_json"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "__acceptance_report_json"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "merged_ledger_json"),
    ("tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py", "method=GET"),
    ("tests/test_hyp005_shadow_collection_orchestrator_4B436625X.py", "test_25x_builds_no_order_collection_plan_from_ready_chain"),
    ("tests/test_hyp005_shadow_collection_orchestrator_4B436625X.py", "test_25x_merges_ledgers_and_deduplicates_observations"),
    ("docs/HYP005_SHADOW_COLLECTION_ORCHESTRATOR_RUNBOOK_4B436625X.md", "HYP-005 Shadow Collection Orchestrator"),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    print("4B.4.3.6.6.25X HYP-005 shadow collection orchestrator / no-order scheduler patch applied")
    for rel in [
        "src/tradebot/research_hyp005_shadow_collection_orchestrator.py",
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "tests/test_hyp005_shadow_collection_orchestrator_4B436625X.py",
    ]:
        path = ROOT / rel
        print(f" - {rel}_exists: {path.exists()}")
        print(f" - {rel}_py_compile_ok: {_compile(path) if path.exists() else False}")
    for rel, marker in CHECKS:
        path = ROOT / rel
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_")
        print(f" - {safe_marker}_present: {present}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
