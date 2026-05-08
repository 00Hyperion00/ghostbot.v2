from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/futures_hypothesis_branch_review.py", [
        "FUTURES_BRANCH_REVIEW_CONTRACT_VERSION",
        "BranchReviewLimits",
        "build_futures_hypothesis_branch_review",
        "BRANCH_REVIEW_PENDING_COMPANION_AUDIT",
        "BRANCH_CLOSED_NO_GO",
        "PRIMARY_CANDIDATE_TOO_SPARSE_OR_OUTLIER_DEPENDENT",
        "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_futures_hypothesis_branch_review_4B436625F.py", [
        "--input-json",
        "--reports-dir",
        "--include-all",
        "--primary-symbol",
        "--companion-symbols",
        "--review-ok",
    ]),
    ("tests/test_futures_hypothesis_branch_review_4B436625F.py", [
        "test_branch_review_pending_when_companion_needs_audit",
        "test_branch_review_closes_when_primary_and_companion_fail_terminal_audit",
        "test_tool_writes_report_from_input_json",
    ]),
    ("docs/FUTURES_HYPOTHESIS_BRANCH_REVIEW_RUNBOOK_4B436625F.md", [
        "Futures Hypothesis Branch Review",
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
    print("4B.4.3.6.6.25F futures hypothesis branch review / candidate closure decision patch applied")
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
            safe_marker = marker.replace("-", "_").replace(" ", "_")
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
