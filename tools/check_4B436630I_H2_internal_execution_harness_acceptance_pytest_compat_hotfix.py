from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H2"
H1_CHECKER = "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py"
H1_TEST = "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py"
EXPECTED_FILES = [
    "README_APPLY_4B436630I_H2.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_PYTEST_COMPAT_HOTFIX_4B436630I_H2.md",
    H1_TEST,
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H2.py",
    "tools/check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
    "tools/rollback_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix.py",
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]


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
            py_compile.compile(str(path), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:  # pragma: no cover - diagnostic only
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def run_checker_cli(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    if not path.exists():
        return {"ok": False, "returncode": 127, "reason": f"CHECKER_MISSING:{rel}"}
    proc = subprocess.run(
        [sys.executable, str(path), "--once-json"],
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
        payload = {
            "ok": False,
            "reason": "CHECKER_OUTPUT_NOT_JSON",
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    payload["returncode"] = proc.returncode
    return payload


def nested_bool(payload: dict[str, Any], *keys: str) -> bool:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return False
        cur = cur.get(key)
    return bool(cur)


def h1_test_source_status(root: Path) -> dict[str, Any]:
    path = root / H1_TEST
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return {
        "path": H1_TEST,
        "exists": path.exists(),
        "uses_cli_helper": "def run_h1_checker_cli" in text,
        "uses_subprocess": "subprocess.run" in text,
        "uses_h1_checker_path": H1_CHECKER in text,
        "does_not_assert_in_process_report_ok": "assert report[\"ok\"] is True" not in text,
    }


def run_check(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = compile_py(root)
    h1_report = run_checker_cli(root, H1_CHECKER)
    h1_checks = h1_report.get("checks") if isinstance(h1_report.get("checks"), dict) else {}
    source = h1_test_source_status(root)
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": True,
        "h1_checker_cli_ok": bool(h1_report.get("ok")) and int(h1_report.get("returncode", 1)) == 0,
        "h1_checker_base_30d_ok": bool(h1_checks.get("base_30d_checker_ok")),
        "h1_checker_base_30h_ok": bool(h1_checks.get("base_30h_checker_ok")),
        "h1_checker_base_30i_ok": bool(h1_checks.get("base_30i_checker_ok")),
        "h1_test_uses_cli_checker": all(
            bool(source.get(key))
            for key in ("exists", "uses_cli_helper", "uses_subprocess", "uses_h1_checker_path", "does_not_assert_in_process_report_ok")
        ),
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
        "h1_test_source_status": source,
        "h1_checker_report": h1_report,
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
        print(f"{CONTRACT_VERSION} internal execution harness acceptance pytest compatibility hotfix ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
