#!/usr/bin/env python3
"""Apply/verify 4B.4.3.6.6.25Y HYP-005 shadow operator runbook patch."""

from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "Hyp005ShadowOperatorAuditLimits"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "ShadowOperatorDashboard"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "ShadowOperatorAuditReport"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "NO_ORDER_OPERATOR_AUDIT_ONLY"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "PAPER_TRANSITION_READINESS_IS_NOT_PAPER_PERMISSION"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "build_hyp005_shadow_operator_audit_report"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "approved_for_live_real"),
    ("src/tradebot/research_hyp005_shadow_operator_runbook.py", "post_requests_allowed"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "__candidate_spec_json"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "__logger_report_json"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "__collection_report_json"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "__acceptance_report_json"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "dashboard_json"),
    ("tools/run_hyp005_shadow_operator_runbook_4B436625Y.py", "runbook_md"),
    ("tests/test_hyp005_shadow_operator_runbook_4B436625Y.py", "test_25y_builds_daily_no_order_audit_pack_from_ready_chain"),
    ("tests/test_hyp005_shadow_operator_runbook_4B436625Y.py", "test_25y_blocks_when_collection_orchestrator_missing"),
    ("tests/test_hyp005_shadow_operator_runbook_4B436625Y.py", "test_tool_writes_report_dashboard_and_runbook"),
    ("docs/HYP005_SHADOW_OPERATOR_RUNBOOK_4B436625Y.md", "HYP-005 Shadow Operator Runbook"),
    ("docs/HYP005_SHADOW_OPERATOR_RUNBOOK_4B436625Y.md", "Paper/live remain blocked"),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    print("4B.4.3.6.6.25Y HYP-005 shadow operator runbook / daily no-order audit patch applied")
    for rel in [
        "src/tradebot/research_hyp005_shadow_operator_runbook.py",
        "tools/run_hyp005_shadow_operator_runbook_4B436625Y.py",
        "tests/test_hyp005_shadow_operator_runbook_4B436625Y.py",
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
