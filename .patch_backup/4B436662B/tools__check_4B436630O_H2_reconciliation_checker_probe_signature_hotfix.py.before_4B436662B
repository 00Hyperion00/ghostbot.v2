from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30O-H2"


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _run_target(root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, str(root / "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py"), "--once-json"],
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
        return {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    target = _run_target(repo_root())
    checks = target.get("checks", {}) if isinstance(target.get("checks"), dict) else {}
    out = {
        "ok": bool(target.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "checks": {
            "checker_wrapper_compat_ok": True,
            "target_30o_checker_ok": bool(target.get("ok")),
            "target_ledger_consumed": bool(checks.get("module_probe_ledger_consumed")),
            "target_reconciliation_ok": bool(checks.get("module_probe_reconciliation_ok")),
            "target_mismatch_zero": bool(checks.get("module_probe_mismatch_zero")),
            "target_sqlite_mirror_ok": bool(checks.get("module_probe_sqlite_mirror_ok")),
            "target_exchange_submit_blocked": bool(checks.get("exchange_submit_still_blocked")),
            "target_live_real_blocked": bool(checks.get("live_real_still_blocked")),
        },
        "target_30o_report_summary": {
            "ok": bool(target.get("ok")),
            "contract_version": target.get("contract_version"),
            "checks": checks,
            "module_probe": target.get("module_probe", {}),
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
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
