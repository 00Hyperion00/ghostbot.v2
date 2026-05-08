from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    "src/tradebot/futures_funding_open_interest_edge_exploration.py",
    "tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py",
    "tests/test_futures_funding_open_interest_edge_exploration_4B436625B.py",
]

MARKERS = {
    "src/tradebot/futures_funding_open_interest_edge_exploration.py": [
        "FUTURES_FUNDING_OI_EDGE_CONTRACT_VERSION",
        "FuturesEdgeSpec",
        "FuturesEdgeLimits",
        "build_futures_funding_open_interest_edge_exploration",
        "evaluate_futures_strategy_edge",
        "EDGE_EXPECTED_EDGE_LOW",
        "EDGE_PROFIT_FACTOR_LOW",
        "NO_FUTURES_FUNDING_OI_EDGE_CANDIDATE_PASSED",
        "approved_for_live_real",
        "get_only_public_futures_data",
        "post_requests_allowed",
    ],
    "tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py": [
        "--symbols",
        "--intervals",
        "--input-csv",
        "--base-url",
        "--review-ok",
        "method=\"GET\"",
        "/fapi/v1/fundingRate",
        "/futures/data/openInterestHist",
        "/futures/data/globalLongShortAccountRatio",
        "/futures/data/takerlongshortRatio",
    ],
    "tests/test_futures_funding_open_interest_edge_exploration_4B436625B.py": [
        "test_futures_edge_exploration_passes_positive_funding_candidate",
        "test_futures_edge_exploration_blocks_negative_candidate",
        "test_tool_writes_report_from_input_csv",
    ],
    "docs/FUTURES_FUNDING_OPEN_INTEREST_EDGE_EXPLORATION_RUNBOOK_4B436625B.md": [
        "Futures Funding / Open Interest Edge Exploration",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    print("4B.4.3.6.6.25B futures funding / open interest edge exploration patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        print(f" - {rel}_exists: {path.exists()}")
        if path.exists() and path.suffix == ".py":
            print(f" - {rel}_py_compile_ok: {compile_ok(path)}")
    for rel, markers in MARKERS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for marker in markers:
            safe = marker.replace("--", "__").replace("/", "_").replace(" ", "_")
            print(f" - {safe}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
