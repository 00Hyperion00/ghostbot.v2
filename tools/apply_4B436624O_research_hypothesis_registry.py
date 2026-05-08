from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/research_hypothesis_registry.py",
    "tools/run_research_hypothesis_registry_4B436624O.py",
    "tests/test_research_hypothesis_registry_4B436624O.py",
]
MARKERS = {
    "src/tradebot/research_hypothesis_registry.py": [
        "RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION",
        "ResearchHypothesis",
        "HypothesisAcceptanceMetrics",
        "build_research_hypothesis_registry",
        "NEXT_HYPOTHESIS_BACKLOG",
        "REGISTRY_READY",
        "NO_VALID_RESEARCH_HYPOTHESIS_REGISTERED",
        "approved_for_live_real",
        "post_requests_allowed",
    ],
    "tools/run_research_hypothesis_registry_4B436624O.py": [
        "--hypotheses-json",
        "--write-default-registry",
        "--previous-decision",
        "--review-ok",
    ],
    "docs/RESEARCH_RESTART_CHARTER_4B436624O.md": [
        "Research Restart Charter",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ],
    "config/research_hypotheses_4B436624O.json": [
        "HYP-001",
        "Higher timeframe trend following",
        "paper_allowed_if_pass",
        "live_allowed_if_pass",
    ],
    "tests/test_research_hypothesis_registry_4B436624O.py": [
        "test_default_registry_is_ready_but_blocks_paper_and_live",
        "test_invalid_live_auto_approval_blocks_registry",
        "test_tool_writes_default_registry_and_report",
    ],
}


def main() -> int:
    results: list[tuple[str, bool]] = []
    for rel in CHECKS:
        path = ROOT / rel
        results.append((f"{rel}_exists", path.exists()))
        if path.exists() and path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                results.append((f"{rel}_py_compile_ok", True))
            except Exception as exc:  # pragma: no cover
                results.append((f"{rel}_py_compile_ok", False))
                results.append((f"{rel}_py_compile_error={exc}", False))
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            results.append((f"{marker.replace('-', '_')}_present", marker in text))

    print("4B.4.3.6.6.24O research restart charter / hypothesis registry patch applied")
    for key, ok in results:
        print(f" - {key}: {ok}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
