from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    (
        "tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py",
        [
            "HYP003_REFINEMENT_CLI_HOTFIX_VERSION",
            "4B.4.3.6.6.25L-H1",
            "_candidate_key_text",
            "selected_next_candidate is None",
            "selected_next_candidate: {_candidate_key_text",
        ],
    ),
    (
        "tests/test_hyp003_candidate_refinement_branch_decision_hotfix_25LH1.py",
        [
            "test_25lh1_declares_cli_hotfix_version",
            "test_25lh1_candidate_key_text_handles_none_and_valid_candidate",
            "test_25lh1_cli_closure_path_no_selected_candidate_does_not_crash",
            "HYP003_BRANCH_CLOSURE_RECOMMENDED",
            "selected_next_candidate: NONE",
        ],
    ),
    (
        "docs/HYP003_CANDIDATE_REFINEMENT_BRANCH_DECISION_HOTFIX_25LH1.md",
        [
            "Branch Closure CLI Hotfix",
            "selected_next_candidate",
            "HYP003_BRANCH_CLOSURE_RECOMMENDED",
            "Paper/live remain blocked",
        ],
    ),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f" - {path}_py_compile_error: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25L-H1 HYP-003 branch closure CLI hotfix applied")
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
