from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28G-H5"
EXPECTED_FILES = [
    "src/tradebot/hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/run_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/apply_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/check_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/rollback_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tests/test_hyp006_counterfactual_filter_candidate_ranking_4B436628G_H5.py",
    "docs/HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_4B436628G_H5.md",
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
    module_path = root / "src/tradebot/hyp006_counterfactual_filter_candidate_ranking.py"
    module_text = module_path.read_text(encoding="utf-8") if module_path.exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "contract_version_ok": f'CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "source_h4_contract_present": "SOURCE_H4_CONTRACT_VERSION" in module_text,
        "ranking_report_present": "build_counterfactual_filter_candidate_ranking_report" in module_text,
        "accepted_review_candidates_present": "accepted_review_candidates" in module_text,
        "do_not_relax_present": "do_not_relax_gate_combos" in module_text,
        "tail_risk_flags_present": "tail_risk_flags" in module_text,
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
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.28G-H5 HYP-006 counterfactual filter candidate ranking patch")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 counterfactual filter candidate ranking patch check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
