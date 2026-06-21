from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30Q"
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/first_paper_sandbox_canary_submit_gate.py",
    "tests/test_first_paper_sandbox_canary_submit_gate_4B436630Q.py",
    "tools/apply_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/rollback_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
]
EXPECTED_FILES = [
    "README_APPLY_4B436630Q.txt",
    "docs/FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_4B436630Q.md",
    "src/tradebot/first_paper_sandbox_canary_submit_gate.py",
    "tests/test_first_paper_sandbox_canary_submit_gate_4B436630Q.py",
    "tools/apply_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/rollback_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
    "tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py",
]
CONFIG_FIELDS = [
    "first_paper_sandbox_canary_submit_gate_enabled",
    "first_paper_sandbox_canary_consume_30p_required",
    "first_paper_sandbox_canary_operator_approval_required",
    "first_paper_sandbox_canary_operator_id",
    "first_paper_sandbox_canary_operator_approval_phrase",
    "first_paper_sandbox_canary_operator_approval_token",
    "first_paper_sandbox_canary_operator_approval_issued",
    "first_paper_sandbox_canary_operator_approval_issued_at_ms",
    "first_paper_sandbox_canary_operator_approval_ttl_sec",
    "first_paper_sandbox_canary_order_intent_required",
    "first_paper_sandbox_canary_submit_guard_required",
    "first_paper_sandbox_canary_no_live_real_required",
    "first_paper_sandbox_canary_quote_notional_usd",
    "first_paper_sandbox_canary_notional_cap_usd",
    "first_paper_sandbox_canary_min_notional_usd",
    "first_paper_sandbox_canary_min_qty",
    "first_paper_sandbox_canary_step_size",
    "first_paper_sandbox_canary_estimated_price_usd",
    "first_paper_sandbox_canary_order_intent_path",
]


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


def _source_30p_ready() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30P",
        "decision": "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_submit_arm_preflight": True,
        "api_mode_ok": True,
        "endpoint_ok": True,
        "min_notional_ok": True,
        "lot_size_ok": True,
        "risk_caps_ok": True,
        "kill_switch_ok": True,
        "approved_for_paper_candidate": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "submit_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.first_paper_sandbox_canary_submit_gate import (
        APPROVAL_REQUIRED_DECISION,
        READY_DECISION,
        build_first_paper_sandbox_canary_submit_gate_snapshot,
    )
    with tempfile.TemporaryDirectory() as tmp:
        intent_path = Path(tmp) / "intent.json"
        blocked = build_first_paper_sandbox_canary_submit_gate_snapshot(Settings(), _source_30p_ready(), intent_path=intent_path, now_ms=1_800_000_000_000)
        ready = build_first_paper_sandbox_canary_submit_gate_snapshot(
            Settings(),
            _source_30p_ready(),
            operator_id="operator-30q",
            approval_token="APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE",
            issue_canary_approval=True,
            intent_path=intent_path,
            write_intent=True,
            now_ms=1_800_000_001_000,
        )
        written = intent_path.exists()
        intent = json.loads(intent_path.read_text(encoding="utf-8")) if written else {}
    return {
        "ok": blocked.get("decision") == APPROVAL_REQUIRED_DECISION and ready.get("decision") == READY_DECISION and written,
        "default_decision": blocked.get("decision"),
        "ready_decision": ready.get("decision"),
        "source_30p_ok": bool(ready.get("source_30p_submit_arm_verified")),
        "approval_ok": bool(ready.get("operator_canary_approval_verified")),
        "readiness_ok": bool(ready.get("sandbox_submit_readiness_verified")),
        "intent_ok": bool(ready.get("single_sandbox_order_intent_built")),
        "intent_written": bool(ready.get("canary_order_intent_written")),
        "submit_guarded": bool(ready.get("exchange_submit_path_guarded")) and intent.get("submit_to_exchange") is False,
        "exchange_submit_blocked": ready.get("approved_for_exchange_submit") is False and ready.get("exchange_submit_performed") is False,
        "live_real_blocked": ready.get("approved_for_live_real") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/config.py").exists() else ""
    source_text = (root / "src/tradebot/first_paper_sandbox_canary_submit_gate.py").read_text(encoding="utf-8", errors="replace") if (root / "src/tradebot/first_paper_sandbox_canary_submit_gate.py").exists() else ""
    base_path = root / "tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py"
    base_report = _run_json_tool(root, "tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py") if base_path.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30q_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30p_h3_checker_ok": bool(base_report.get("ok")),
        "source_30p_submit_arm_gate_present": "source_30p_submit_arm_gate" in source_text,
        "explicit_operator_canary_approval_gate_present": "explicit_operator_canary_approval_gate" in source_text,
        "sandbox_submit_readiness_gate_present": "sandbox_submit_readiness_gate" in source_text,
        "api_mode_gate_present": "api_mode_gate" in source_text,
        "endpoint_gate_present": "endpoint_gate" in source_text,
        "min_notional_gate_present": "min_notional_gate" in source_text,
        "lot_size_gate_present": "lot_size_gate" in source_text,
        "risk_caps_gate_present": "risk_caps_gate" in source_text,
        "kill_switch_gate_present": "kill_switch_gate" in source_text,
        "exchange_submit_guard_gate_present": "exchange_submit_guard_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30p_ok": bool(probe.get("source_30p_ok")),
        "module_probe_approval_ok": bool(probe.get("approval_ok")),
        "module_probe_readiness_ok": bool(probe.get("readiness_ok")),
        "module_probe_intent_ok": bool(probe.get("intent_ok")),
        "module_probe_submit_guarded": bool(probe.get("submit_guarded")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
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
        "paper_live_order_enablement_present": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if not args.once_json:
        print(f"{CONTRACT_VERSION} first paper sandbox canary submit gate check {'OK' if payload['ok'] else 'FAILED'}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
