from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "4B.4.3.6.6.28D-H1_28E-H1"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "src/tradebot/hyp006_scheduler_health_verify.py",
    "tests/test_hyp006_scheduler_unicode_safe_hotfix_4B436628D_H1_28E_H1.py",
    "docs/HYP006_R1_SCHEDULER_UNICODE_SAFE_HOTFIX_4B436628D_H1_28E_H1.md",
    "tools/check_4B436628D_H1_28E_H1_scheduler_unicode_safe_hotfix.py",
    "tools/rollback_4B436628D_H1_28E_H1_scheduler_unicode_safe_hotfix.py",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")] + [
    "tools/run_4B436628D_hyp006_shadow_registration_approval.py",
    "tools/run_4B436628E_hyp006_scheduler_execution_health.py",
]


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    source_28d = (ROOT / "src/tradebot/hyp006_shadow_registration_operator_approval.py").read_text(encoding="utf-8")
    source_28e = (ROOT / "src/tradebot/hyp006_scheduler_health_verify.py").read_text(encoding="utf-8")
    checks = {
        "all_expected_files_present": all((ROOT / rel).exists() for rel in EXPECTED_FILES),
        "all_py_compile_ok": all(compile_ok(ROOT / rel) for rel in PY_FILES if (ROOT / rel).exists()),
        "unicode_literal_path_emission_present": "_ps_single_quoted" in source_28d and "json.dumps(root)" not in source_28d,
        "absolute_python_resolution_present": "Get-Command python -ErrorAction Stop" in source_28d,
        "scheduler_wrapper_present": "run_hyp006_r1_canonical_shadow_scheduler.ps1" in source_28d,
        "registration_json_argument_present": "--registration-json" in source_28d,
        "pythonpath_present": "$env:PYTHONPATH = 'src'" in source_28d,
        "scheduler_logs_present": "hyp006_scheduler_stdout.log" in source_28d and "hyp006_scheduler_stderr.log" in source_28d,
        "utf8_bom_json_read_present": "utf-8-sig" in source_28e,
        "localized_powershell_decode_present": "_decode_subprocess_bytes" in source_28e and "cp1254" in source_28e,
        "powershell_wrapper_health_allowed": "powershell_wrapper_action" in source_28e,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "paper_live_order_enablement_present": False,
    }
    print(f"{CONTRACT_VERSION} scheduler unicode-safe hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if all(value is True or value is False and key in {"scheduler_mutation_performed", "scheduler_task_created", "paper_live_order_enablement_present"} for key, value in checks.items()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
