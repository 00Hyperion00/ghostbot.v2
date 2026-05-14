from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION"),
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "DEFAULT_HYP005_SYMBOLS_10"),
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "HYP005_SYMBOL_COVERAGE_EXPANSION_READY"),
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "build_hyp005_symbol_coverage_report"),
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "approved_for_scheduler_regeneration"),
    ("src/tradebot/research_hyp005_symbol_coverage_expansion.py", "approved_for_live_real=False"),
    ("tools/run_hyp005_symbol_coverage_expansion_4B436625AA.py", "--write-config"),
    ("tests/test_hyp005_symbol_coverage_expansion_4B436625AA.py", "test_default_10_symbol_coverage_passes"),
    ("docs/HYP005_SYMBOL_COVERAGE_EXPANSION_4B436625AA.md", "Controlled Symbol Coverage Expansion Gate"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/research_hyp005_symbol_coverage_expansion.py",
    "tools/run_hyp005_symbol_coverage_expansion_4B436625AA.py",
    "tests/test_hyp005_symbol_coverage_expansion_4B436625AA.py",
)


def main() -> int:
    results: list[tuple[str, bool]] = []
    for rel_path in COMPILE_TARGETS:
        path = PROJECT_ROOT / rel_path
        exists = path.exists()
        results.append((f"{rel_path}_exists", exists))
        if exists:
            try:
                py_compile.compile(str(path), doraise=True)
                results.append((f"{rel_path}_py_compile_ok", True))
            except py_compile.PyCompileError:
                results.append((f"{rel_path}_py_compile_ok", False))

    for rel_path, marker in CHECKS:
        path = PROJECT_ROOT / rel_path
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        safe_marker = marker.replace(" ", "_").replace("/", "_")
        results.append((f"{safe_marker}_present", present))

    print("4B.4.3.6.6.25AA HYP-005 controlled symbol coverage expansion patch applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
