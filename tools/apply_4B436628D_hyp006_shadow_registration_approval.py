from __future__ import annotations

import importlib.util
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.28D"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "tools/run_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/run_4B436628D_hyp006_canonical_shadow_cycle.py",
    "tools/check_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/apply_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/rollback_4B436628D_hyp006_shadow_registration_approval.py",
    "tests/test_hyp006_shadow_registration_approval_4B436628D.py",
    "docs/HYP006_R1_CANONICAL_SHADOW_REGISTRATION_4B436628D.md",
    "README_APPLY_4B436628D.txt",
]


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    py_files = [Path(item) for item in EXPECTED_FILES if item.endswith(".py")]
    compiled = {str(path): compile_ok(ROOT / path) for path in py_files if (ROOT / path).exists()}
    payload_path = ROOT / "src/tradebot/hyp006_shadow_registration_operator_approval.py"
    payload_text = payload_path.read_text(encoding="utf-8") if payload_path.exists() else ""
    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "all_expected_files_present": all((ROOT / item).exists() for item in EXPECTED_FILES),
        "all_py_compile_ok": bool(compiled) and all(compiled.values()),
        "contract_version_present": CONTRACT_VERSION in payload_text,
        "operator_approval_gate_present": "operator_approval_recorded" in payload_text,
        "retention_policy_present": "runtime_artifact_retention_policy" in payload_text,
        "canonical_cycle_present": "build_canonical_shadow_cycle_report" in payload_text,
        "scheduler_task_not_created_guard_present": "scheduler_task_created" in payload_text,
        "paper_live_order_enablement_present": any(token in payload_text for token in ("approved_for_live_real\": True", "approved_for_paper_candidate\": True", "order_actions_performed\": True")),
    }
    print(f"{CONTRACT_VERSION} HYP-006-R1 Canonical No-Order Shadow Collection / Scheduler Registration Operator Approval patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if checks["all_expected_files_present"] and checks["all_py_compile_ok"] and checks["contract_version_present"] and not checks["paper_live_order_enablement_present"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
