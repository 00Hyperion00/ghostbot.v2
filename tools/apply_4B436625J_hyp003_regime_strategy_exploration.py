from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp003_regime_strategy_exploration.py", [
        "HYP003_EXPLORATION_CONTRACT_VERSION",
        "StrategyFamilySpec",
        "RegimeStrategyExplorationLimits",
        "build_hyp003_regime_strategy_exploration_report",
        "HYP003_EXPLORATION_PASS",
        "HYP003_EXPLORATION_BLOCK",
        "NO_HYP003_REGIME_STRATEGY_CANDIDATE_PASSED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp003_regime_strategy_exploration_4B436625J.py", [
        "__input_json",
        "__input_csv",
        "__symbols",
        "__intervals",
        "__review_ok",
        "method=\"GET\"",
        "public market-data GET only",
    ]),
    ("tests/test_hyp003_regime_strategy_exploration_4B436625J.py", [
        "test_validate_hyp003_selection_from_25i_report",
        "test_regime_strategy_candidate_can_pass_with_positive_edge",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/HYP003_REGIME_STRATEGY_EXPLORATION_RUNBOOK_4B436625J.md", [
        "HYP-003 Regime-Specific Strategy Family Exploration Gate",
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
    print("4B.4.3.6.6.25J HYP-003 regime-specific strategy family exploration gate patch applied")
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
            print(f" - {marker.replace('-', '_').replace(' ', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
