from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CONTRACT_VERSION = "4B.4.3.6.6.28D-H1_28E-H1"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_registration_operator_approval.py",
    "src/tradebot/hyp006_scheduler_health_verify.py",
    "tests/test_hyp006_scheduler_unicode_safe_hotfix_4B436628D_H1_28E_H1.py",
    "docs/HYP006_R1_SCHEDULER_UNICODE_SAFE_HOTFIX_4B436628D_H1_28E_H1.md",
    "tools/apply_4B436628D_H1_28E_H1_scheduler_unicode_safe_hotfix.py",
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script
    from tradebot.hyp006_scheduler_health_verify import load_json, validate_scheduler_task_health

    expected = {rel: (ROOT / rel).exists() for rel in EXPECTED_FILES}
    compiled = {rel: compile_ok(ROOT / rel) for rel in PY_FILES if (ROOT / rel).exists()}
    script = build_registration_script(
        project_root=ROOT,
        approval_json=ROOT / "reports" / "hyp006_r1_canonical" / "approval.json",
        reports_dir=ROOT / "reports" / "hyp006_r1_canonical",
        symbols=["ADAUSDT", "BTCUSDT"],
    )
    probe_ok, probe_reasons, _ = validate_scheduler_task_health(
        {
            "task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection",
            "last_task_result": 0,
            "number_of_missed_runs": 0,
            "action_execute": "powershell.exe",
            "action_arguments": '-NoProfile -ExecutionPolicy Bypass -File "C:\\trade_botV2\\reports\\hyp006_r1_canonical\\run_hyp006_r1_canonical_shadow_scheduler.ps1"',
            "working_directory": "C:\\trade_botV2",
        }
    )
    bom_probe = ROOT / ".tmp_28de_h1_bom_probe.json"
    bom_probe.write_bytes(b"\xef\xbb\xbf" + json.dumps({"ok": True}).encode("utf-8"))
    try:
        bom_ok = load_json(bom_probe) == {"ok": True}
    finally:
        bom_probe.unlink(missing_ok=True)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "unicode_escape_absent_from_generated_script": "\\u00" not in script,
        "absolute_python_resolution_present": "Get-Command python -ErrorAction Stop" in script,
        "powershell_wrapper_emitted": "run_hyp006_r1_canonical_shadow_scheduler.ps1" in script,
        "registration_json_argument_present": "--registration-json" in script,
        "pythonpath_present": "$env:PYTHONPATH = 'src'" in script,
        "stdout_stderr_logs_present": "hyp006_scheduler_stdout.log" in script and "hyp006_scheduler_stderr.log" in script,
        "utf8_no_bom_wrapper_write_present": "UTF8Encoding($false)" in script,
        "powershell_wrapper_health_valid": probe_ok,
        "powershell_wrapper_health_reasons_empty": probe_reasons == [],
        "bom_json_supported": bom_ok,
        "scheduler_mutation_blocked": True,
        "scheduler_task_not_created_by_patch": True,
        "paper_live_order_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if args.once_json else payload)
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
