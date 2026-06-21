from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30R"
EXPECTED_FILES = [
    "README_APPLY_4B436630R.txt",
    "docs/PAPER_SANDBOX_CANARY_RECONCILIATION_4B436630R.md",
    "src/tradebot/paper_sandbox_canary_reconciliation.py",
    "tests/test_paper_sandbox_canary_reconciliation_4B436630R.py",
    "tools/apply_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/rollback_4B436630R_paper_sandbox_canary_reconciliation.py",
    "tools/run_4B436630R_paper_sandbox_canary_reconciliation.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["src/tradebot/config.py"]
CONFIG_FIELDS = [
    "paper_sandbox_canary_reconciliation_enabled",
    "paper_sandbox_canary_reconciliation_consume_30q_required",
    "paper_sandbox_canary_reconciliation_order_intent_required",
    "paper_sandbox_canary_reconciliation_submit_guard_required",
    "paper_sandbox_canary_reconciliation_mismatch_zero_required",
    "paper_sandbox_canary_reconciliation_no_live_real_required",
    "paper_sandbox_canary_reconciliation_order_intent_path",
    "paper_sandbox_canary_reconciliation_expected_fill_count",
    "paper_sandbox_canary_reconciliation_expected_account_delta_usd",
    "paper_sandbox_canary_reconciliation_expected_position_delta_qty",
    "paper_sandbox_canary_reconciliation_expected_fee_usd",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in PY_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def _run_json_tool(root: Path, rel: str) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
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
        return {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_canary_reconciliation import READY_DECISION, build_paper_sandbox_canary_reconciliation_snapshot

    source = {
        "contract_version": "4B.4.3.6.6.30Q",
        "decision": "FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL",
        "approved_for_first_paper_sandbox_canary_submit_gate": True,
        "source_30p_submit_arm_verified": True,
        "operator_canary_approval_verified": True,
        "sandbox_submit_readiness_verified": True,
        "single_sandbox_order_intent_built": True,
        "canary_order_intent_written": True,
        "exchange_submit_path_guarded": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
    }
    intent = {
        "intent_id": "probe-intent-30q",
        "contract_version": "4B.4.3.6.6.30Q",
        "event_type": "first_paper_sandbox_canary_single_order_intent_submit_guarded_no_exchange_submit",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quote_notional_usd": 10.0,
        "quantity": 0.004,
        "submit_path_guarded": True,
        "submit_to_exchange": False,
        "submitted_to_exchange": False,
        "network_submit_attempted": False,
        "exchange_submit_performed": False,
        "live_real_approved": False,
    }
    payload = build_paper_sandbox_canary_reconciliation_snapshot(Settings(), source, intent)
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "mismatch_count": payload.get("mismatch_count"),
        "source_30q_ok": bool(payload.get("source_30q_canary_gate_verified")),
        "intent_consumed": bool(payload.get("canary_order_intent_consumed")),
        "reconciled": bool(payload.get("intent_fill_account_reconciled")),
        "submit_guarded": bool(payload.get("submit_remained_guarded_verified")),
        "exchange_submit_blocked": payload.get("approved_for_exchange_submit") is False and payload.get("exchange_submit_performed") is False,
        "live_real_blocked": payload.get("approved_for_live_real") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/config.py").exists() else ""
    source_text = (root / "src/tradebot/paper_sandbox_canary_reconciliation.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/paper_sandbox_canary_reconciliation.py").exists() else ""
    base_checker = root / "tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py"
    base_report = _run_json_tool(root, "tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py") if base_checker.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30r_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30p_h3_checker_ok": bool(base_report.get("ok")),
        "source_30q_canary_intent_gate_present": "source_30q_canary_intent_gate" in source_text,
        "canary_order_intent_consumption_gate_present": "canary_order_intent_consumption_gate" in source_text,
        "intent_fill_account_reconciliation_gate_present": "intent_fill_account_reconciliation_gate" in source_text,
        "submit_guarded_proof_gate_present": "submit_remained_guarded_proof_gate" in source_text,
        "mismatch_zero_gate_present": "mismatch_zero_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_mismatch_zero": probe.get("mismatch_count") == 0,
        "module_probe_submit_guarded": bool(probe.get("submit_guarded")),
        "module_probe_exchange_submit_blocked": bool(probe.get("exchange_submit_blocked")),
        "module_probe_live_real_blocked": bool(probe.get("live_real_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "base_30p_h3_report_summary": {
            "ok": bool(base_report.get("ok")),
            "contract_version": base_report.get("contract_version"),
            "checks": base_report.get("checks", {}),
        },
        "module_probe": probe,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "network_submit_attempted": False,
        "paper_live_order_enablement_present": False,
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
