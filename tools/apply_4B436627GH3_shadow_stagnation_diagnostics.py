from __future__ import annotations

import py_compile
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H3"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "src" / "tradebot" / "hyp005_shadow_stagnation_diagnostics.py",
    ROOT / "tools" / "run_4B436627GH3_shadow_stagnation_diagnostics.py",
    ROOT / "tools" / "check_4B436627GH3_shadow_stagnation_diagnostics.py",
    ROOT / "tools" / "rollback_4B436627GH3_shadow_stagnation_diagnostics.py",
    ROOT / "tests" / "test_shadow_stagnation_diagnostics_4B436627GH3.py",
    ROOT / "docs" / "SHADOW_OBSERVATION_STAGNATION_DIAGNOSTICS_4B436627GH3.md",
    ROOT / "README_APPLY_4B436627GH3.txt",
]


def _compile_ok(path: Path) -> bool:
    if path.suffix != ".py":
        return True
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError as exc:
        print(str(exc), file=sys.stderr)
        return False


def _contains(path: Path, text: str) -> bool:
    return text in path.read_text(encoding="utf-8") if path.exists() else False


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in FILES if not path.exists()]
    compile_results = {str(path.relative_to(ROOT)): _compile_ok(path) for path in FILES if path.exists()}
    module = ROOT / "src" / "tradebot" / "hyp005_shadow_stagnation_diagnostics.py"
    runner = ROOT / "tools" / "run_4B436627GH3_shadow_stagnation_diagnostics.py"
    module_text = module.read_text(encoding="utf-8") if module.exists() else ""
    runner_text = runner.read_text(encoding="utf-8") if runner.exists() else ""
    paper_live_order_enablement_present = any(
        marker in module_text + runner_text
        for marker in (
            "orders_allowed=True",
            "paper_trading_allowed=True",
            "live_trading_allowed=True",
            "approved_for_live_real: True",
            "approved_for_paper_candidate: True",
        )
    )
    checks = {
        "all_expected_files_present": not missing,
        "all_py_compile_ok": all(compile_results.values()) if compile_results else False,
        "contract_version_present": CONTRACT_VERSION in module_text and CONTRACT_VERSION in runner_text,
        "near_miss_audit_present": "near_miss_count" in module_text,
        "filter_rejection_counts_present": "filter_rejection_counts" in module_text,
        "stagnation_status_present": "STAGNATED" in module_text,
        "runner_requires_review_ok": "--review-ok" in runner_text,
        "no_order_research_guard_present": "no_order_research_diagnostics_only" in module_text,
        "paper_live_order_enablement_present": paper_live_order_enablement_present,
    }
    ok = all(value for key, value in checks.items() if key != "paper_live_order_enablement_present") and not paper_live_order_enablement_present
    print(f"{CONTRACT_VERSION} Shadow Observation Stagnation Diagnostics / Candidate Signal Near-Miss Audit / No-Order Research Bottleneck Report patch applied")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if missing:
        print(f" - missing_files: {missing}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
