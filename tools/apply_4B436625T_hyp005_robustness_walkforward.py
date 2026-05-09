from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_robustness_walkforward.py", [
        "HYP005_ROBUSTNESS_CONTRACT_VERSION",
        "Hyp005RobustnessLimits",
        "build_hyp005_robustness_walkforward_report",
        "HYP005_ROBUSTNESS_PASS",
        "HYP005_ROBUSTNESS_BLOCK",
        "ROBUST_MEAN_EDGE_LOW_AFTER_SMALL_SAMPLE_PENALTY",
        "ROBUST_WALK_FORWARD_STABILITY_LOW",
        "ROBUST_TOP_WIN_DEPENDENCY_HIGH",
        "ROBUST_WICK_DEPENDENCY_HIGH",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp005_robustness_walkforward_4B436625T.py", [
        "__input_json",
        "__input_csv",
        "__symbols",
        "__interval",
        "__review_ok",
        "method=\"GET\"",
        "public market data GET only",
        "HYP-005 robustness/walk-forward",
    ]),
    ("tests/test_hyp005_robustness_walkforward_4B436625T.py", [
        "test_validate_hyp005_25s_pass_report_and_extracts_spec",
        "test_robustness_candidate_can_pass_with_persistent_sweeps",
        "test_robustness_blocks_when_exploration_not_pass",
        "test_robustness_applies_small_sample_penalty_and_blocks_weak_sample",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/HYP005_ROBUSTNESS_WALKFORWARD_RUNBOOK_4B436625T.md", [
        "HYP-005 Robustness / Walk-Forward Confirmation Gate",
        "HYP005_ROBUSTNESS_PASS",
        "small-sample penalty",
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
    print("4B.4.3.6.6.25T HYP-005 robustness / walk-forward confirmation gate patch applied")
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
            safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_").replace('"', "")
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
