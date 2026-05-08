from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/timeframe_symbol_strategy_edge_exploration.py",
    "tools/run_timeframe_symbol_strategy_edge_exploration_4B436624M.py",
    "tests/test_timeframe_symbol_strategy_edge_exploration_4B436624M.py",
]
MARKERS = {
    "src/tradebot/timeframe_symbol_strategy_edge_exploration.py": [
        "TIMEFRAME_SYMBOL_EDGE_CONTRACT_VERSION",
        "StrategyEdgeSpec",
        "EdgeExplorationLimits",
        "build_timeframe_symbol_strategy_edge_exploration",
        "evaluate_strategy_edge",
        "EDGE_EXPECTED_EDGE_LOW",
        "EDGE_PROFIT_FACTOR_LOW",
        "approved_for_live_real",
    ],
    "tools/run_timeframe_symbol_strategy_edge_exploration_4B436624M.py": [
        "REPORT_PREFIX",
        "--symbols",
        "--intervals",
        "--input-csv",
        "get_only_public_market_data",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_timeframe_symbol_strategy_edge_exploration_4B436624M.py": [
        "test_edge_exploration_passes_positive_trend_candidate",
        "test_edge_exploration_blocks_negative_edge_candidate",
        "test_tool_writes_report_from_input_csv",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        return False
    return True


def main() -> int:
    print("4B.4.3.6.6.24M timeframe / symbol / strategy edge exploration patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        print(f" - {rel}_exists: {path.exists()}")
        print(f" - {rel}_py_compile_ok: {compile_ok(path) if path.exists() and path.suffix == '.py' else False}")
    doc = ROOT / "docs/TIMEFRAME_SYMBOL_STRATEGY_EDGE_EXPLORATION_RUNBOOK_4B436624M.md"
    print(f" - docs/TIMEFRAME_SYMBOL_STRATEGY_EDGE_EXPLORATION_RUNBOOK_4B436624M.md_exists: {doc.exists()}")
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            safe = marker.replace("-", "_").replace("=", "_")
            print(f" - {safe}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
