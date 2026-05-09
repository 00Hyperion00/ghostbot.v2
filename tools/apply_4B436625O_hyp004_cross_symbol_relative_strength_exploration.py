from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp004_cross_symbol_relative_strength_exploration.py", [
        "HYP004_EXPLORATION_CONTRACT_VERSION",
        "CrossSymbolStrategySpec",
        "CrossSymbolExplorationLimits",
        "build_hyp004_cross_symbol_relative_strength_exploration_report",
        "HYP004_EXPLORATION_PASS",
        "HYP004_EXPLORATION_BLOCK",
        "NO_HYP004_RELATIVE_STRENGTH_CANDIDATE_PASSED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp004_cross_symbol_relative_strength_exploration_4B436625O.py", [
        "__input_json",
        "__input_csv",
        "__symbols",
        "__interval",
        "__review_ok",
        "method=\"GET\"",
        "public market data GET only",
    ]),
    ("tests/test_hyp004_cross_symbol_relative_strength_exploration_4B436625O.py", [
        "test_validate_hyp004_selection_from_25n_report",
        "test_relative_strength_candidate_can_pass_with_persistent_rotation",
        "test_tool_writes_report_from_input_csv",
    ]),
    ("docs/HYP004_CROSS_SYMBOL_RELATIVE_STRENGTH_EXPLORATION_RUNBOOK_4B436625O.md", [
        "HYP-004 Cross-Symbol Relative Strength Exploration Gate",
        "Training remains blocked",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"COMPILE_ERROR {path}: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25O HYP-004 cross-symbol relative strength exploration gate patch applied")
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
        normalized = text.replace("-", "_").replace(" ", "_")
        for marker in markers:
            present = marker.replace("-", "_").replace(" ", "_") in normalized
            print(f" - {marker.replace('-', '_').replace(' ', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
