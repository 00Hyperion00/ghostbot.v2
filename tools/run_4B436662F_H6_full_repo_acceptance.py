from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "4B436662F-H6"
PATCH_VERSION = "4B.4.3.6.6.62F-H6"

SAFETY_FALSE: dict[str, bool] = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "exchange_submit_performed": False,
    "network_order_submit_performed": False,
    "paper_order_submit_performed": False,
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "runtime_start_performed": False,
    "trading_action_performed": False,
}

TARGETED_TESTS = (
    "tests/test_release_audit_legacy_api_drift_compatibility_4B436661_H1.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_v2_4B436661_H2.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_h3_4B436661_H3.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_h4_4B436661_H4.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_h5_4B436661_H5.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_h6_4B436661_H6.py",
    "tests/test_release_audit_legacy_api_drift_compatibility_h7_4B436661_H7.py",
    "tests/test_full_repo_regression_stabilization_4B436662A.py",
    "tests/test_full_repo_regression_stabilization_4B436662B.py",
    "tests/test_full_repo_regression_stabilization_4B436662C.py",
    "tests/test_full_repo_regression_stabilization_4B436662D.py",
    "tests/test_full_repo_regression_stabilization_4B436662E.py",
    "tests/test_full_repo_regression_stabilization_4B436662F.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H1.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H2.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H3.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H4.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H5.py",
    "tests/test_full_repo_regression_stabilization_4B436662F_H6.py",
)


def _run(name: str, command: list[str], env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "command": command,
        "stdout_tail": completed.stdout[-12000:],
        "stderr_tail": completed.stderr[-12000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--skip-full-pytest", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    existing_targeted = [path for path in TARGETED_TESTS if (ROOT / path).exists()]

    stages: list[dict[str, Any]] = []
    stages.append(
        _run(
            "h6_behavior_checker",
            [sys.executable, "tools/check_4B436662F_H6_final_full_repo_contract_closure.py", "--once-json"],
            env,
        )
    )
    stages.append(
        _run(
            "targeted_phase61_phase62_regression",
            [sys.executable, "-m", "pytest", "-q", *existing_targeted],
            env,
        )
    )
    if not args.skip_full_pytest:
        stages.append(_run("full_pytest", [sys.executable, "-m", "pytest", "-q", "tests"], env))
    stages.append(
        _run(
            "compileall",
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "-x",
                r"(_patch_backup|_patch_payload|legacy_patches)",
                "src",
                "tools",
                "tests",
            ],
            env,
        )
    )

    ok = all(stage["ok"] for stage in stages)
    report: dict[str, Any] = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "decision": (
            "FINAL_FULL_REPO_ACCEPTANCE_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
            if ok
            else "FINAL_FULL_REPO_ACCEPTANCE_BLOCKED"
        ),
        "stage_count": len(stages),
        "stage_ready_count": sum(1 for stage in stages if stage["ok"]),
        "stages": stages,
        **SAFETY_FALSE,
    }
    reports_dir = ROOT / args.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "4B436662F_H6_full_repo_acceptance.json"
    report["report_path"] = str(report_path.resolve())
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
