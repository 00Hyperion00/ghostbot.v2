from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

PATCH_ID = "4B436662F-H4"
PATCH_VERSION = "4B.4.3.6.6.62F-H4"
ROOT = Path.cwd()

SAFETY_FALSE: dict[str, bool] = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_actions_performed": False,
    "trading_action_performed": False,
    "runtime_start_performed": False,
    "reload_performed": False,
    "training_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "private_api_access_allowed": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
}


def _contract(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def build_report() -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    hyp006 = ROOT / "src/tradebot/hyp006_shadow_registration_operator_approval.py"
    try:
        py_compile.compile(str(hyp006), doraise=True)
        contracts.append(_contract("hyp006_py_compile", True))
    except Exception as exc:  # noqa: BLE001
        contracts.append(_contract("hyp006_py_compile", False, str(exc)))

    try:
        sys.path.insert(0, str(ROOT / "src"))
        mod = importlib.import_module("tradebot.hyp006_shadow_registration_operator_approval")
        script = mod.build_registration_script(
            project_root=ROOT,
            approval_json=ROOT / "reports/hyp006_r1_canonical/approval.json",
            reports_dir=ROOT / "reports/hyp006_r1_canonical",
            symbols=["ADAUSDT"],
        )
        contracts.append(_contract("hyp006_registration_script_markers", all(marker in script for marker in (
            "$Python = (Get-Command python -ErrorAction Stop).Source",
            "$env:PYTHONPATH = 'src'",
            "--registration-approval-json",
            "--registration-json",
            "hyp006_scheduler_stdout.log",
            "hyp006_scheduler_stderr.log",
        ))))
    except Exception as exc:  # noqa: BLE001
        contracts.append(_contract("hyp006_registration_script_markers", False, str(exc)))

    ready = sum(1 for c in contracts if c["ok"])
    ok = ready == len(contracts)
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "decision": "HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_BLOCKED",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "contract_count": len(contracts),
        "contract_ready_count": ready,
        "contracts": contracts,
        **SAFETY_FALSE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
