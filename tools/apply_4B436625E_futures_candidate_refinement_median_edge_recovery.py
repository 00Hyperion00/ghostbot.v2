from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("src/tradebot/futures_candidate_refinement_median_edge_recovery.py", [
        "FUTURES_REFINEMENT_CONTRACT_VERSION",
        "FuturesRefinementSpec",
        "MedianEdgeFilterSpec",
        "MedianEdgeRecoveryLimits",
        "build_futures_candidate_refinement_report",
        "evaluate_filtered_signals",
        "REFINEMENT_MEDIAN_EDGE_LOW",
        "REFINEMENT_TOP_WIN_DEPENDENCY_HIGH",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py", [
        "--input-json",
        "--spec-json",
        "--input-csv",
        "--review-ok",
        "method=\"GET\"",
        "safe_fetch_futures_data_series",
        "clamp_futures_data_start_ms",
        "futures median-edge refinement",
    ]),
    ("tests/test_futures_candidate_refinement_median_edge_recovery_4B436625E.py", [
        "test_refinement_passes_positive_median_edge_candidate",
        "test_refinement_blocks_negative_median_edge_candidate",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/FUTURES_CANDIDATE_REFINEMENT_MEDIAN_EDGE_RECOVERY_RUNBOOK_4B436625E.md", [
        "Futures Candidate Refinement",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ]),
]


def compile_file(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as exc:
        print(f"COMPILE_ERROR {path}: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25E futures candidate refinement / median edge recovery patch applied")
    ok = True
    for rel, markers in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = compile_file(path)
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
