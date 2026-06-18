from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28G-H4"
EXPECTED_FILES = [
    "src/tradebot/hyp006_near_miss_outcome_attribution.py",
    "tools/run_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/apply_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/check_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/rollback_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tests/test_hyp006_near_miss_outcome_attribution_4B436628G_H4.py",
    "docs/HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_4B436628G_H4.md",
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
    module_text = (root / "src/tradebot/hyp006_near_miss_outcome_attribution.py").read_text(encoding="utf-8") if (root / "src/tradebot/hyp006_near_miss_outcome_attribution.py").exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "contract_version_ok": f'CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "source_h3_contract_present": "SOURCE_H3_CONTRACT_VERSION" in module_text,
        "outcome_attribution_present": "attribute_near_miss_event" in module_text,
        "gate_combo_summary_present": "gate_combo_outcome_summary" in module_text,
        "trigger_benchmark_present": "trigger_benchmark_summary" in module_text,
        "parameter_relaxation_blocked": '"approved_for_parameter_relaxation_candidate": False' in module_text,
        "paper_live_order_blocked": '"approved_for_paper_candidate": False' in module_text and '"approved_for_live_real": False' in module_text and '"order_actions_performed": False' in module_text,
        "training_blocked": '"training_performed": False' in module_text and '"reload_performed": False' in module_text,
        "scheduler_mutation_blocked": '"scheduler_mutation_performed": False' in module_text and '"scheduler_task_created": False' in module_text,
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
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.28G-H4 HYP-006 near-miss outcome attribution patch")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 near-miss outcome attribution patch check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
