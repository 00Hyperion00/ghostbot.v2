from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_backlog_advancement.py", [
        "RESEARCH_BACKLOG_ADVANCEMENT_CONTRACT_VERSION",
        "ResearchHypothesisBacklogItem",
        "ResearchBacklogAdvancementLimits",
        "build_research_backlog_advancement_gate",
        "NEXT_HYPOTHESIS_SELECTED",
        "BACKLOG_ADVANCEMENT_BLOCK",
        "HYPOTHESIS_CLOSURE_EVIDENCE_CONFIRMED",
        "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_research_backlog_advancement_4B436625I.py", [
        "--input-json",
        "--reports-dir",
        "--include-all",
        "--registry-json",
        "--hypothesis-id",
        "--review-ok",
        "proposed_registry_json",
    ]),
    ("tests/test_research_backlog_advancement_4B436625I.py", [
        "test_backlog_advancement_selects_next_hypothesis_after_25h_closure",
        "test_backlog_advancement_blocks_when_closure_pack_missing",
        "test_tool_writes_report_and_registry_snapshot",
    ]),
    ("docs/RESEARCH_BACKLOG_ADVANCEMENT_RUNBOOK_4B436625I.md", [
        "Research Backlog Advancement",
        "HYP-002",
        "NEXT_HYPOTHESIS_SELECTED",
        "Training remains blocked",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:
        print(f"COMPILE_ERROR {path}: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25I research backlog advancement / next hypothesis selection gate patch applied")
    ok = True
    for rel, markers in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = _compile(path)
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
        text = path.read_text(encoding="utf-8") if exists else ""
        for marker in markers:
            present = marker in text
            safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_")
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
