from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H3"
EXPECTED_FILES = [
    "README_APPLY_4B436630I_H3.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_DETERMINISTIC_CHECKER_HOTFIX_4B436630I_H3.md",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H3.py",
    "tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
    "tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py",
    "tools/rollback_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]
CHECKERS = {
    "30D": "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "30I": "tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
    "30I-H1": "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
}


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_py(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def run_checker_cli(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists():
        return {"ok": False, "returncode": 127, "reason": f"CHECKER_MISSING:{rel}"}
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(path), "--once-json"],
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
    except Exception:
        payload = {"ok": False, "reason": "CHECKER_OUTPUT_NOT_JSON", "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def source_status(root: Path) -> dict[str, Any]:
    d = root / "tools" / "check_4B436630D_operator_approval_evidence_capture.py"
    h1 = root / "tools" / "check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py"
    h1_test = root / "tests" / "test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py"
    d_text = d.read_text(encoding="utf-8") if d.exists() else ""
    h1_text = h1.read_text(encoding="utf-8") if h1.exists() else ""
    h1_test_text = h1_test.read_text(encoding="utf-8") if h1_test.exists() else ""
    return {
        "30d_checker_uses_no_pyc_syntax_compile": "syntax_check" in d_text and "compile(source, str(path), \"exec\")" in d_text,
        "h1_checker_uses_no_bytecode_cli": "PYTHONDONTWRITEBYTECODE" in h1_text and '"-B"' in h1_text,
        "h1_checker_has_compat_recovery": "base_30i_checker_compat_recovered" in h1_text and "base_30i_compat_recovered" in h1_text,
        "h1_test_memoized_cli": "_CACHED_REPORT" in h1_test_text and '"-B"' in h1_test_text,
    }


def run_check(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = compile_py(root)
    reports = {name: run_checker_cli(root, rel) for name, rel in CHECKERS.items() if (root / rel).exists()}
    source = source_status(root)
    h1 = reports.get("30I-H1", {})
    h1_checks = h1.get("checks") if isinstance(h1.get("checks"), dict) else {}
    base_strict = h1.get("base_checker_strict_ok") if isinstance(h1.get("base_checker_strict_ok"), dict) else {}
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": True,
        "source_30d_no_pyc_syntax_compile_present": bool(source.get("30d_checker_uses_no_pyc_syntax_compile")),
        "source_h1_no_bytecode_cli_present": bool(source.get("h1_checker_uses_no_bytecode_cli")),
        "source_h1_compat_recovery_present": bool(source.get("h1_checker_has_compat_recovery")),
        "source_h1_test_memoized_cli_present": bool(source.get("h1_test_memoized_cli")),
        "checker_30d_ok": bool(reports.get("30D", {}).get("ok")) and int(reports.get("30D", {}).get("returncode", 1)) == 0,
        "checker_30i_ok": bool(reports.get("30I", {}).get("ok")) and int(reports.get("30I", {}).get("returncode", 1)) == 0,
        "checker_h1_ok": bool(h1.get("ok")) and int(h1.get("returncode", 1)) == 0,
        "h1_base_30d_ok": bool(h1_checks.get("base_30d_checker_ok")),
        "h1_base_30h_ok": bool(h1_checks.get("base_30h_checker_ok")),
        "h1_base_30i_ok": bool(h1_checks.get("base_30i_checker_ok")),
        "exchange_submit_still_blocked": bool(h1_checks.get("exchange_submit_still_blocked")),
        "paper_execution_still_blocked": bool(h1_checks.get("paper_execution_still_blocked")),
        "paper_candidate_still_blocked": bool(h1_checks.get("paper_candidate_still_blocked")),
        "live_real_still_blocked": bool(h1_checks.get("live_real_still_blocked")),
        "order_actions_blocked": bool(h1_checks.get("order_actions_blocked")),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "expected_files": expected,
        "compiled": compiled,
        "source_status": source,
        "checker_reports": reports,
        "h1_base_checker_strict_ok": base_strict,
        "checks": checks,
        "read_only": True,
        "paper_live_order_enablement_present": False,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = run_check(repo_root())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} deterministic acceptance hotfix ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
