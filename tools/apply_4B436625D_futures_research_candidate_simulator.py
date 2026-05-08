from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/futures_research_candidate_simulator.py", [
        "FUTURES_RESEARCH_SIMULATOR_CONTRACT_VERSION",
        "FuturesResearchCandidateSpec",
        "DryRunSimulatorLimits",
        "build_futures_research_candidate_simulator_report",
        "evaluate_dry_run_candidate",
        "DRY_RUN_EXPECTED_EDGE_LOW",
        "DRY_RUN_PROFIT_FACTOR_LOW",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_futures_research_candidate_simulator_4B436625D.py", [
        "--input-json",
        "--spec-json",
        "--input-csv",
        "--write-spec",
        "--review-ok",
        "method=\"GET\"",
        "safe_fetch_futures_data_series",
    ]),
    ("tests/test_futures_research_candidate_simulator_4B436625D.py", [
        "test_dry_run_simulator_passes_positive_futures_candidate",
        "test_dry_run_simulator_blocks_negative_edge_candidate",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/FUTURES_RESEARCH_CANDIDATE_SIMULATOR_RUNBOOK_4B436625D.md", [
        "Futures Research Candidate Dry-Run Signal Simulator",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ]),
    ("config/futures_research_candidate_4B436625D.json", [
        "funding_trend_exhaustion",
        "BTCUSDT",
        "4h",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as exc:
        print(exc)
        return False


def main() -> int:
    print("4B.4.3.6.6.25D futures research candidate dry-run signal simulator patch applied")
    ok = True
    for rel_path, markers in CHECKS:
        path = ROOT / rel_path
        exists = path.exists()
        print(f" - {rel_path}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compile_ok = _compile(path)
            print(f" - {rel_path}_py_compile_ok: {compile_ok}")
            ok = ok and compile_ok
        text = path.read_text(encoding="utf-8") if exists else ""
        for marker in markers:
            present = marker in text
            marker_name = marker.replace("-", "_").replace("/", "_").replace(" ", "_")
            print(f" - {marker_name}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
