from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_backlog_after_hyp003_closure.py", [
        "RESEARCH_BACKLOG_HYP003_ADVANCEMENT_CONTRACT_VERSION",
        "HypothesisAcceptanceCriteria",
        "ResearchHypothesisBacklogItem",
        "build_research_backlog_after_hyp003_closure",
        "NEXT_HYPOTHESIS_SELECTED",
        "HYP003_CLOSURE_CONFIRMED",
        "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_research_backlog_after_hyp003_closure_4B436625N.py", [
        "__input_json",
        "__reports_dir",
        "__registry_json",
        "__hypothesis_id",
        "__review_ok",
        "registry_snapshot_json",
    ]),
    ("tests/test_research_backlog_after_hyp003_closure_4B436625N.py", [
        "test_25n_selects_next_hypothesis_after_hyp003_closure",
        "test_25n_blocks_when_hyp003_closure_missing",
        "test_tool_writes_report_and_registry_snapshot",
    ]),
    ("docs/RESEARCH_BACKLOG_AFTER_HYP003_CLOSURE_RUNBOOK_4B436625N.md", [
        "Research Backlog Advancement After HYP-003 Closure",
        "NEXT_HYPOTHESIS_SELECTED",
        "Training remains blocked",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f" - {path}_py_compile_error: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25N research backlog advancement after HYP-003 closure patch applied")
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
        normalized = text.replace("-", "_").replace(" ", "_")
        for marker in markers:
            present = marker.replace("-", "_").replace(" ", "_") in normalized
            print(f" - {marker.replace('-', '_').replace(' ', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
