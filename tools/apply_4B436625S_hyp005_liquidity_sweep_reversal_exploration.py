from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    (
        "src/tradebot/research_hyp005_liquidity_sweep_reversal_exploration.py",
        [
            "HYP005_EXPLORATION_CONTRACT_VERSION",
            "LiquiditySweepStrategySpec",
            "LiquiditySweepExplorationLimits",
            "build_hyp005_liquidity_sweep_reversal_exploration_report",
            "HYP005_EXPLORATION_PASS",
            "HYP005_EXPLORATION_BLOCK",
            "NO_HYP005_LIQUIDITY_SWEEP_CANDIDATE_PASSED",
            "DIAGNOSTIC_STRATEGY_NOT_APPROVABLE",
            "approved_for_live_real",
            "post_requests_allowed",
        ],
    ),
    (
        "tools/run_hyp005_liquidity_sweep_reversal_exploration_4B436625S.py",
        [
            "__input_json",
            "__input_csv",
            "__symbols",
            "__interval",
            "__review_ok",
            "method=\"GET\"",
            "public market data GET only",
        ],
    ),
    (
        "tests/test_hyp005_liquidity_sweep_reversal_exploration_4B436625S.py",
        [
            "test_validate_hyp005_selection_from_25r_report",
            "test_liquidity_sweep_candidate_can_pass_with_reversal_edges",
            "test_tool_writes_report_from_input_csv",
        ],
    ),
    (
        "docs/HYP005_LIQUIDITY_SWEEP_REVERSAL_EXPLORATION_RUNBOOK_4B436625S.md",
        [
            "HYP-005 Liquidity Sweep Reversal Exploration Gate",
            "Training remains blocked",
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
    print("4B.4.3.6.6.25S HYP-005 liquidity sweep reversal exploration gate patch applied")
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
        normalized_text = text.replace("-", "_")
        for marker in markers:
            safe_marker = marker.replace("-", "_").replace(" ", "_").replace("/", "_")
            present = marker.replace("-", "_") in normalized_text
            print(f" - {safe_marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
