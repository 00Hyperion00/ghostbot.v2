from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28G-H8"
EXPECTED_FILES = [
    "src/tradebot/hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/run_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/apply_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/check_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/rollback_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tests/test_hyp006_bnbusdt_overlay_oos_evaluation_4B436628G_H8.py",
    "docs/HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_4B436628G_H8.md",
]


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def build_report(root: Path) -> dict[str, object]:
    expected = {name: (root / name).exists() for name in EXPECTED_FILES}
    compiled = {name: compile_ok(root / name) for name in EXPECTED_FILES if name.endswith(".py") and (root / name).exists()}
    module_path = root / "src/tradebot/hyp006_bnbusdt_overlay_oos_evaluation.py"
    module_text = module_path.read_text(encoding="utf-8") if module_path.exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "contract_version_ok": f'CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "source_h7_contract_present": "SOURCE_H7_CONTRACT_VERSION" in module_text,
        "oos_delta_present": "oos_delta_summary" in module_text,
        "latest_previous_comparison_present": "previous_bnbusdt_measurement_summary" in module_text and "latest_bnbusdt_measurement_summary" in module_text,
        "runtime_activation_blocked": '"runtime_overlay_activation_performed": False' in module_text and '"approved_for_runtime_overlay_activation_candidate": False' in module_text,
        "parameter_relaxation_blocked": '"approved_for_parameter_relaxation_candidate": False' in module_text,
        "paper_live_order_blocked": '"approved_for_paper_candidate": False' in module_text and '"approved_for_live_real": False' in module_text and '"order_actions_performed": False' in module_text,
        "training_blocked": '"training_performed": False' in module_text and '"reload_performed": False' in module_text,
        "scheduler_mutation_blocked": '"scheduler_mutation_performed": False' in module_text and '"scheduler_task_created": False' in module_text,
        "strategy_parameter_mutation_blocked": '"strategy_parameter_mutation_performed": False' in module_text,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "read_only": True,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.28G-H8 HYP-006 BNBUSDT overlay OOS evaluation patch")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 BNBUSDT overlay OOS evaluation patch check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
