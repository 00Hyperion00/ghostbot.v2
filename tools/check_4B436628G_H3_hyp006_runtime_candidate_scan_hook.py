from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.28G-H3"
EXPECTED_FILES = (
    "src/tradebot/hyp006_shadow_runner_dry_run.py",
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "tools/check_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py",
    "tools/apply_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py",
    "tools/rollback_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py",
    "tools/run_4B436628G_H3_hyp006_runtime_candidate_scan_hook.py",
    "tests/test_hyp006_runtime_candidate_scan_hook_4B436628G_H3.py",
    "docs/HYP006_R1_RUNTIME_CANDIDATE_SCAN_HOOK_4B436628G_H3.md",
)
PY_FILES = tuple(path for path in EXPECTED_FILES if path.endswith(".py"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def run_checks(root: Path) -> dict[str, Any]:
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled: dict[str, bool] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
        except Exception:
            compiled[rel] = False
        else:
            compiled[rel] = True
    runner = _read(root / "src/tradebot/hyp006_shadow_runner_dry_run.py")
    approval = _read(root / "src/tradebot/hyp006_shadow_registration_operator_approval.py")
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in runner,
        "runtime_hook_function_present": "scan_hyp006_short_probe_observations_with_diagnostics" in runner,
        "gate_block_counter_present": "gate_block_counter" in runner,
        "near_miss_counter_present": "near_miss_count" in runner,
        "candidate_scan_artifact_writer_present": "CANDIDATE_SCAN_ARTIFACT_PREFIX" in approval and "write_candidate_scan_markdown" in approval,
        "parameter_relaxation_blocked": "approved_for_parameter_relaxation_candidate\": False" in runner,
        "paper_live_order_blocked": "approved_for_paper_candidate\": False" in runner and "approved_for_live_real\": False" in runner,
        "training_blocked": "training_performed\": False" in runner,
        "scheduler_mutation_blocked": "scheduler_mutation_performed\": False" in runner,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "read_only": True,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 28G-H3 HYP-006 runtime candidate scan hook patch.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = run_checks(args.root)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 runtime candidate scan hook checker")
        for key, value in payload["checks"].items():
            print(f" - {key}: {value}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
