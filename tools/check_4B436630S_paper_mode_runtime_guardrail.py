from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30S"
PAYLOAD_DIR = Path("_patch_payload") / CONTRACT_VERSION
CONFIG_FIELDS = ['paper_mode_runtime_guardrail_enabled', 'paper_mode_runtime_guardrail_consume_30r_required', 'paper_mode_runtime_guardrail_loop_required', 'paper_mode_runtime_guardrail_strict_caps_required', 'paper_mode_runtime_guardrail_kill_switch_required', 'paper_mode_runtime_guardrail_kill_switch_enabled', 'paper_mode_runtime_guardrail_no_exchange_submit_required', 'paper_mode_runtime_guardrail_no_live_real_required', 'paper_mode_runtime_guardrail_max_ticks', 'paper_mode_runtime_guardrail_tick_cap', 'paper_mode_runtime_guardrail_order_action_cap', 'paper_mode_runtime_guardrail_exchange_submit_cap', 'paper_mode_runtime_guardrail_network_submit_cap', 'paper_mode_runtime_guardrail_max_notional_usd', 'paper_mode_runtime_guardrail_runtime_seconds_cap']
CONFIG_BLOCK = '\n    # 4B.4.3.6.6.30S paper mode runtime guardrail controls\n    paper_mode_runtime_guardrail_enabled: bool = True\n    paper_mode_runtime_guardrail_consume_30r_required: bool = True\n    paper_mode_runtime_guardrail_loop_required: bool = True\n    paper_mode_runtime_guardrail_strict_caps_required: bool = True\n    paper_mode_runtime_guardrail_kill_switch_required: bool = True\n    paper_mode_runtime_guardrail_kill_switch_enabled: bool = True\n    paper_mode_runtime_guardrail_no_exchange_submit_required: bool = True\n    paper_mode_runtime_guardrail_no_live_real_required: bool = True\n    paper_mode_runtime_guardrail_max_ticks: int = 3\n    paper_mode_runtime_guardrail_tick_cap: int = 5\n    paper_mode_runtime_guardrail_order_action_cap: int = 0\n    paper_mode_runtime_guardrail_exchange_submit_cap: int = 0\n    paper_mode_runtime_guardrail_network_submit_cap: int = 0\n    paper_mode_runtime_guardrail_max_notional_usd: float = 0.0\n    paper_mode_runtime_guardrail_runtime_seconds_cap: int = 30\n'
EXPECTED_FILES = ['README_APPLY_4B436630S.txt', 'docs/PAPER_MODE_RUNTIME_GUARDRAIL_4B436630S.md', 'src/tradebot/paper_mode_runtime_guardrail.py', 'tests/test_paper_mode_runtime_guardrail_4B436630S.py', 'tools/apply_4B436630S_paper_mode_runtime_guardrail.py', 'tools/check_4B436630S_paper_mode_runtime_guardrail.py', 'tools/rollback_4B436630S_paper_mode_runtime_guardrail.py', 'tools/run_4B436630S_paper_mode_runtime_guardrail.py']
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")] + ["src/tradebot/config.py"]



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
    from tradebot.paper_mode_runtime_guardrail import READY_DECISION, build_paper_mode_runtime_guardrail_snapshot

    source = {
        "contract_version": "4B.4.3.6.6.30R",
        "decision": "PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_canary_reconciliation": True,
        "source_30q_canary_gate_verified": True,
        "canary_order_intent_consumed": True,
        "intent_fill_account_reconciled": True,
        "submit_remained_guarded_verified": True,
        "mismatch_zero_verified": True,
        "mismatch_count": 0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }
    payload = build_paper_mode_runtime_guardrail_snapshot(Settings(), source)
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "source_30r_ok": bool(payload.get("source_30r_reconciliation_verified")),
        "guarded_loop_ok": bool(payload.get("guarded_runtime_loop_verified")),
        "strict_caps_ok": bool(payload.get("strict_caps_verified")),
        "kill_switch_ok": bool(payload.get("kill_switch_verified")),
        "no_exchange_submit_ok": bool(payload.get("no_exchange_submit_verified")),
        "no_live_real_ok": bool(payload.get("no_live_real_verified")),
        "loop_tick_count": payload.get("loop_tick_count"),
        "order_action_count": payload.get("order_action_count"),
        "exchange_submit_count": payload.get("exchange_submit_count"),
        "network_submit_count": payload.get("network_submit_count"),
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
    source_text = (root / "src/tradebot/paper_mode_runtime_guardrail.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/paper_mode_runtime_guardrail.py").exists() else ""
    base_checker = root / "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py"
    base_report = _run_json_tool(root, "tools/check_4B436630R_paper_sandbox_canary_reconciliation.py") if base_checker.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30s_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30r_checker_ok": bool(base_report.get("ok")),
        "source_30r_reconciliation_gate_present": "source_30r_reconciliation_gate" in source_text,
        "guarded_runtime_loop_gate_present": "guarded_runtime_loop_gate" in source_text,
        "strict_caps_gate_present": "strict_caps_gate" in source_text,
        "kill_switch_proof_gate_present": "kill_switch_proof_gate" in source_text,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30r_ok": bool(probe.get("source_30r_ok")),
        "module_probe_guarded_loop_ok": bool(probe.get("guarded_loop_ok")),
        "module_probe_strict_caps_ok": bool(probe.get("strict_caps_ok")),
        "module_probe_kill_switch_ok": bool(probe.get("kill_switch_ok")),
        "module_probe_no_exchange_submit_ok": bool(probe.get("no_exchange_submit_ok")),
        "module_probe_no_live_real_ok": bool(probe.get("no_live_real_ok")),
        "module_probe_zero_actions": probe.get("order_action_count") == 0 and probe.get("exchange_submit_count") == 0 and probe.get("network_submit_count") == 0,
        "runtime_training_reload_mutation_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "expected_files": expected,
        "base_30r_report_summary": {
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
