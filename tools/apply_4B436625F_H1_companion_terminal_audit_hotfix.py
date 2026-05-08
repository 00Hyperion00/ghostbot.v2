from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/futures_hypothesis_branch_review.py", [
        "FUTURES_BRANCH_REVIEW_HOTFIX_VERSION",
        "4B.4.3.6.6.25F-H1",
        "_nested_get",
        "_candidate_spec_fields",
        "_merge_metric_fields",
        "25D/25E schemas",
        "DRY_RUN_OOS_EDGE_LOW",
        "REFINEMENT_MEAN_EDGE_LOW",
        "REFINEMENT_MEDIAN_EDGE_LOW",
    ]),
    ("tests/test_futures_hypothesis_branch_review_hotfix_25FH1.py", [
        "test_25fh1_normalizes_actual_25d_selected_mapping",
        "test_25fh1_normalizes_actual_25e_candidate_spec_selected_metrics",
        "test_25fh1_closes_branch_when_primary_and_actual_companion_terminal_audits_block",
        "BRANCH_CLOSED_NO_GO",
        "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED",
    ]),
    ("docs/FUTURES_HYPOTHESIS_BRANCH_REVIEW_HOTFIX_25FH1.md", [
        "Companion Terminal Audit Recognition Hotfix",
        "BRANCH_CLOSED_NO_GO",
        "25D",
        "25E",
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
    print("4B.4.3.6.6.25F-H1 companion terminal audit recognition hotfix applied")
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
