from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp003_candidate_refinement_branch_decision.py", [
        "HYP003_REFINEMENT_CONTRACT_VERSION",
        "Hyp003BranchDecisionLimits",
        "build_hyp003_candidate_refinement_branch_decision",
        "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS",
        "HYP003_BRANCH_CLOSURE_RECOMMENDED",
        "HYP003_SELECTED_CANDIDATE_ROBUSTNESS_BLOCK",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py", [
        "--input-json",
        "--reports-dir",
        "--include-all",
        "--review-ok",
        "next_candidate_25k_json",
    ]),
    ("tests/test_hyp003_candidate_refinement_branch_decision_4B436625L.py", [
        "test_25l_selects_next_25j_pass_candidate_after_25k_block",
        "test_25l_recommends_branch_closure_when_no_alternate_candidate",
        "test_tool_writes_report_and_next_candidate_json",
    ]),
    ("docs/HYP003_CANDIDATE_REFINEMENT_BRANCH_DECISION_RUNBOOK_4B436625L.md", [
        "HYP-003 Candidate Refinement",
        "Paper/live remain blocked",
        "HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:
        print(f" - {path}_py_compile_error: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25L HYP-003 candidate refinement / branch decision gate patch applied")
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
