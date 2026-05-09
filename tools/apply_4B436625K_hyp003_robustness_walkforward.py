from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp003_robustness_walkforward.py", [
        "HYP003_ROBUSTNESS_CONTRACT_VERSION",
        "Hyp003CandidateSpec",
        "Hyp003RobustnessLimits",
        "build_hyp003_robustness_walkforward_report",
        "HYP003_ROBUSTNESS_PASS",
        "HYP003_ROBUSTNESS_BLOCK",
        "ROBUST_WALK_FORWARD_STABILITY_LOW",
        "ROBUST_OOS_EDGE_LOW",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp003_robustness_walkforward_4B436625K.py", [
        "--input-json",
        "--input-csv",
        "--review-ok",
        "method=\"GET\"",
        "public market data GET only",
    ]),
    ("tests/test_hyp003_robustness_walkforward_4B436625K.py", [
        "test_parse_selected_candidate_from_25j_report",
        "test_robustness_gate_passes_balanced_positive_candidate",
        "test_robustness_gate_blocks_negative_oos_candidate",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/HYP003_ROBUSTNESS_WALKFORWARD_RUNBOOK_4B436625K.md", [
        "HYP-003 Robustness",
        "Walk-Forward Confirmation Gate",
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
    print("4B.4.3.6.6.25K HYP-003 robustness / walk-forward confirmation gate patch applied")
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
            print(f" - {marker.replace('-', '_').replace(' ', '_').replace('/', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
