from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp004_relative_strength_refinement.py", [
        "HYP004_REFINEMENT_CONTRACT_VERSION",
        "RelativeStrengthRefinementSpec",
        "RelativeStrengthRefinementLimits",
        "build_hyp004_relative_strength_refinement_report",
        "HYP004_REFINEMENT_PASS",
        "HYP004_REFINEMENT_BLOCK",
        "NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED",
        "DIAGNOSTIC_REFINEMENT_NOT_APPROVABLE",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp004_relative_strength_refinement_4B436625P.py", [
        "__input_json",
        "__input_csv",
        "__symbols",
        "__interval",
        "__review_ok",
        "method=\"GET\"",
        "public market data GET only",
        "next_candidate_25q_json",
    ]),
    ("tests/test_hyp004_relative_strength_refinement_4B436625P.py", [
        "test_validate_hyp004_25o_report_accepts_laggard_reversion_selection",
        "test_refined_candidate_can_pass_with_persistent_relative_reversion",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/HYP004_RELATIVE_STRENGTH_REFINEMENT_RUNBOOK_4B436625P.md", [
        "HYP-004 Relative Strength Candidate Refinement",
        "Training remains blocked",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"COMPILE_ERROR {path}: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25P HYP-004 relative strength candidate refinement / approvable strategy gate patch applied")
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
        normalized = text.replace("-", "_")
        for marker in markers:
            present = marker.replace("-", "_") in normalized
            safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_").replace('"', "")
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
