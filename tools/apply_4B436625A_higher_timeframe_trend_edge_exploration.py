from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/higher_timeframe_trend_edge_exploration.py",
    "tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py",
    "tests/test_higher_timeframe_trend_edge_exploration_4B436625A.py",
    "docs/HIGHER_TIMEFRAME_TREND_EDGE_EXPLORATION_RUNBOOK_4B436625A.md",
]
MARKERS = {
    "src/tradebot/higher_timeframe_trend_edge_exploration.py": [
        "HIGHER_TIMEFRAME_TREND_EDGE_CONTRACT_VERSION",
        "HigherTimeframeStrategySpec",
        "HigherTimeframeTrendLimits",
        "build_timeframe_symbol_strategy_edge_exploration",
        "evaluate_strategy_edge",
        "EDGE_EXPECTED_EDGE_LOW",
        "EDGE_PROFIT_FACTOR_LOW",
        "approved_for_live_real",
        "get_only_public_market_data",
        "post_requests_allowed",
    ],
    "tools/run_higher_timeframe_trend_edge_exploration_4B436625A.py": [
        "--symbols",
        "--intervals",
        "--input-csv",
        "--review-ok",
        "method=\"GET\"",
    ],
    "tests/test_higher_timeframe_trend_edge_exploration_4B436625A.py": [
        "test_edge_exploration_passes_positive_higher_timeframe_trend_candidate",
        "test_edge_exploration_blocks_negative_edge_candidate",
        "test_tool_writes_report_from_input_csv",
    ],
    "docs/HIGHER_TIMEFRAME_TREND_EDGE_EXPLORATION_RUNBOOK_4B436625A.md": [
        "Higher Timeframe Trend Edge Exploration",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ],
}


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    print("4B.4.3.6.6.25A higher timeframe trend edge exploration patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if rel.endswith(".py"):
            print(f" - {rel}_py_compile_ok: {_compile(path) if exists else False}")
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            safe = marker.replace("-", "_").replace(" ", "_").replace('"', "")
            print(f" - {safe}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
