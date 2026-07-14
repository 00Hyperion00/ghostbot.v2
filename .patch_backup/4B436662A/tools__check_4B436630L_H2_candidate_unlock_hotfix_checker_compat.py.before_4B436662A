from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30L-H2"
EXPECTED_FILES = [
    "README_APPLY_4B436630L_H2.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_HOTFIX_CHECKER_COMPAT_4B436630L_H2.md",
    "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
    "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/apply_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tools/rollback_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L_H2.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    compiled: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            compiled[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            compiled[rel] = {"ok": False, "error": str(exc)}
    return compiled


def _run_json(root: Path, rel: str) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(root / rel), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=300,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _source_has_compat(root: Path) -> bool:
    path = root / "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return (
        "explicit_paper_candidate_unlock_gate_present" in text
        and "sandbox_only_order_enablement_preflight_gate_present" in text
        and "explicit_candidate_unlock_gate_present" in text
        and "sandbox_order_enablement_preflight_gate_present" in text
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    h1_report = _run_json(root, "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py")
    target_report = _run_json(root, "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py")
    base_30k_report = _run_json(root, "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py")
    h1_checks = h1_report.get("checks", {}) if isinstance(h1_report.get("checks"), dict) else {}
    target_checks = target_report.get("checks", {}) if isinstance(target_report.get("checks"), dict) else {}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": True,
        "h1_checker_ok": bool(h1_report.get("ok")),
        "target_30l_checker_ok": bool(target_report.get("ok")),
        "base_30k_checker_ok": bool(base_30k_report.get("ok")),
        "h1_source_checker_key_compat_present": _source_has_compat(root),
        "h1_explicit_unlock_gate_present": bool(h1_checks.get("explicit_unlock_gate_present")),
        "h1_sandbox_preflight_gate_present": bool(h1_checks.get("sandbox_preflight_gate_present")),
        "target_explicit_unlock_gate_present": bool(target_checks.get("explicit_paper_candidate_unlock_gate_present")),
        "target_sandbox_preflight_gate_present": bool(target_checks.get("sandbox_only_order_enablement_preflight_gate_present")),
        "paper_candidate_unlocked_candidate_only": bool(target_checks.get("paper_candidate_unlocked_candidate_only")),
        "paper_execution_still_blocked": bool(target_checks.get("paper_execution_still_blocked")),
        "exchange_submit_still_blocked": bool(target_checks.get("exchange_submit_still_blocked")),
        "live_real_still_blocked": bool(target_checks.get("live_real_still_blocked")),
        "runtime_training_reload_mutation_blocked": bool(target_checks.get("runtime_training_reload_mutation_blocked")),
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "h1_report_summary": {
            "ok": bool(h1_report.get("ok")),
            "contract_version": h1_report.get("contract_version"),
            "checks": h1_checks,
        },
        "target_30l_report_summary": {
            "ok": bool(target_report.get("ok")),
            "contract_version": target_report.get("contract_version"),
            "checks": target_checks,
            "module_probe": target_report.get("module_probe", {}),
        },
        "base_30k_report_summary": {
            "ok": bool(base_30k_report.get("ok")),
            "contract_version": base_30k_report.get("contract_version"),
            "checks": base_30k_report.get("checks", {}),
        },
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
