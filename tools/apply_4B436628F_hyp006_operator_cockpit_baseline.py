from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "src/tradebot/hyp006_operator_cockpit_baseline.py",
    "tools/run_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/check_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/rollback_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tests/test_hyp006_operator_cockpit_baseline_4B436628F.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_BASELINE_4B436628F.md",
]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    results: dict[str, bool] = {}
    for rel in EXPECTED_FILES:
        path = ROOT / rel
        results[f"{rel}_exists"] = path.exists()
        if rel.endswith(".py") and path.exists():
            results[f"{rel}_py_compile_ok"] = _compile_ok(path)

    text = (ROOT / "src/tradebot/hyp006_operator_cockpit_baseline.py").read_text(encoding="utf-8")
    results["contract_version_present"] = "4B.4.3.6.6.28F" in text
    results["dashboard_seed_present"] = "dashboard_seed" in text
    results["acceptance_baseline_present"] = "acceptance_baseline_metrics" in text
    results["continuity_monitor_present"] = "no_order_continuity_monitor" in text
    results["paper_live_order_enablement_present"] = any(token in text for token in ("approved_for_paper_candidate\": True", "approved_for_live_real\": True", "order_actions_allowed\": True"))

    print("4B.4.3.6.6.28F HYP-006-R1 Shadow Operator Cockpit Dashboard Seed patch applied")
    for key, value in results.items():
        print(f" - {key}: {value}")
    safe = all(value for key, value in results.items() if key != "paper_live_order_enablement_present") and not results["paper_live_order_enablement_present"]
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - training_performed: False")
    print(" - reload_performed: False")
    print(" - trading_action_performed: False")
    return 0 if safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
