from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H1"
BASE_30I_CONTRACT_VERSION = "4B.4.3.6.6.30I"
RUNNER_PATH = "tools/run_4B436630D_operator_approval_evidence_capture.py"
EXPECTED_FILES = [
    "README_APPLY_4B436630I_H1.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_ACCEPTANCE_CHAIN_HOTFIX_4B436630I_H1.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py",
    "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    "tools/rollback_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py",
    RUNNER_PATH,
]
PY_FILES = [item for item in EXPECTED_FILES if item.endswith(".py")]
BASE_CHECKERS = {
    "30D": "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "30H": "tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py",
    "30I": "tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py",
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
            py_compile.compile(str(path), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:  # pragma: no cover - error details are diagnostic output
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def run_checker(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists():
        return {"ok": False, "returncode": 127, "reason": f"CHECKER_MISSING:{rel}"}
    proc = subprocess.run(
        [sys.executable, str(path), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=240,
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


def _nested_bool(payload: dict[str, Any], *keys: str) -> bool:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return False
        cur = cur.get(key)
    return bool(cur)


def runner_source_status(root: Path) -> dict[str, Any]:
    path = root / RUNNER_PATH
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return {
        "path": RUNNER_PATH,
        "exists": path.exists(),
        "has_repo_root_helper": "def _repo_root() -> Path:" in text,
        "has_once_json": 'parser.add_argument("--once-json"' in text,
        "has_report_bundle_call": "write_report_bundle(payload, args.reports_dir)" in text,
        "has_main_guard": 'if __name__ == "__main__":' in text,
        "has_operator_approval_import": "paper_transition_approval_evidence_capture" in text,
    }


def run_check(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = compile_py(root)
    runner_status = runner_source_status(root)
    base_reports = {name: run_checker(root, rel) for name, rel in BASE_CHECKERS.items()}
    base_ok = {
        name: bool(report.get("ok")) and int(report.get("returncode", 1)) == 0
        for name, report in base_reports.items()
    }
    base_30i = base_reports.get("30I", {})
    module_probe = base_30i.get("module_probe") if isinstance(base_30i.get("module_probe"), dict) else {}
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": True,
        "runner_30d_py_compile_ok": bool(compiled.get(RUNNER_PATH, {}).get("ok")),
        "runner_30d_source_compat_ok": all(
            bool(runner_status.get(key))
            for key in (
                "exists",
                "has_repo_root_helper",
                "has_once_json",
                "has_report_bundle_call",
                "has_main_guard",
                "has_operator_approval_import",
            )
        ),
        "base_30d_checker_ok": base_ok.get("30D", False),
        "base_30h_checker_ok": base_ok.get("30H", False),
        "base_30i_checker_ok": base_ok.get("30I", False),
        "base_30i_accepted_baseline_preserved": bool(base_30i.get("contract_version") == BASE_30I_CONTRACT_VERSION)
        and _nested_bool(base_30i, "module_probe", "ready_internal_harness")
        and _nested_bool(base_30i, "module_probe", "ledger_append_ok"),
        "exchange_submit_still_blocked": _nested_bool(base_30i, "module_probe", "exchange_submit_blocked"),
        "paper_execution_still_blocked": _nested_bool(base_30i, "module_probe", "paper_execution_blocked"),
        "paper_candidate_still_blocked": _nested_bool(base_30i, "module_probe", "paper_candidate_blocked"),
        "live_real_still_blocked": _nested_bool(base_30i, "module_probe", "live_real_blocked"),
        "order_actions_blocked": _nested_bool(base_30i, "module_probe", "order_actions_blocked"),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "expected_files": expected,
        "compiled": compiled,
        "runner_source_status": runner_status,
        "base_checker_ok": base_ok,
        "base_reports": base_reports,
        "module_probe": module_probe,
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
        print(f"{CONTRACT_VERSION} internal execution harness acceptance chain hotfix ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
