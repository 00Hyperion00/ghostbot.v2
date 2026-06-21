from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = '4B.4.3.6.6.30T'
CONFIG_FIELDS = ['paper_soak_evidence_window_enabled', 'paper_soak_evidence_window_consume_30s_required', 'paper_soak_evidence_window_min_cycles_required', 'paper_soak_evidence_window_cycle_count', 'paper_soak_evidence_window_cycle_cap', 'paper_soak_evidence_window_cap_continuity_required', 'paper_soak_evidence_window_kill_switch_required', 'paper_soak_evidence_window_kill_switch_enabled', 'paper_soak_evidence_window_no_exchange_submit_required', 'paper_soak_evidence_window_no_live_real_required', 'paper_soak_evidence_window_order_action_cap', 'paper_soak_evidence_window_exchange_submit_cap', 'paper_soak_evidence_window_network_submit_cap', 'paper_soak_evidence_window_max_notional_usd', 'paper_soak_evidence_window_runtime_seconds_cap']
EXPECTED_FILES = ['README_APPLY_4B436630T.txt', 'docs/PAPER_SOAK_EVIDENCE_WINDOW_4B436630T.md', 'src/tradebot/paper_soak_evidence_window.py', 'tests/test_paper_soak_evidence_window_4B436630T.py', 'tools/apply_4B436630T_paper_soak_evidence_window.py', 'tools/check_4B436630T_paper_soak_evidence_window.py', 'tools/rollback_4B436630T_paper_soak_evidence_window.py', 'tools/run_4B436630T_paper_soak_evidence_window.py']
PY_FILES = ['src/tradebot/paper_soak_evidence_window.py', 'tests/test_paper_soak_evidence_window_4B436630T.py', 'tools/apply_4B436630T_paper_soak_evidence_window.py', 'tools/check_4B436630T_paper_soak_evidence_window.py', 'tools/rollback_4B436630T_paper_soak_evidence_window.py', 'tools/run_4B436630T_paper_soak_evidence_window.py', 'src/tradebot/config.py']


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
    from tradebot.paper_soak_evidence_window import READY_DECISION, build_paper_soak_evidence_window_snapshot

    source = {
        "contract_version": "4B.4.3.6.6.30S",
        "decision": "PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_mode_runtime_guardrail": True,
        "source_30r_reconciliation_verified": True,
        "guarded_runtime_loop_verified": True,
        "strict_caps_verified": True,
        "kill_switch_verified": True,
        "no_exchange_submit_verified": True,
        "no_live_real_verified": True,
        "loop_tick_count": 3,
        "order_action_count": 0,
        "exchange_submit_count": 0,
        "network_submit_count": 0,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "network_submit_attempted": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }
    payload = build_paper_soak_evidence_window_snapshot(Settings(), source)
    return {
        "ok": payload.get("decision") == READY_DECISION,
        "decision": payload.get("decision"),
        "source_30s_ok": bool(payload.get("source_30s_guardrail_verified")),
        "multi_cycle_soak_ok": bool(payload.get("multi_cycle_soak_verified")),
        "cap_continuity_ok": bool(payload.get("cap_continuity_verified")),
        "kill_switch_continuity_ok": bool(payload.get("kill_switch_continuity_verified")),
        "no_exchange_submit_ok": bool(payload.get("no_exchange_submit_verified")),
        "no_live_real_ok": bool(payload.get("no_live_real_verified")),
        "soak_cycle_count": payload.get("soak_cycle_count"),
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
    config_path = root / "src/tradebot/config.py"
    config_text = config_path.read_text(encoding="utf-8", errors="replace") if config_path.exists() else ""
    source_path = root / "src/tradebot/paper_soak_evidence_window.py"
    source_text = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else ""
    base_checker = root / "tools/check_4B436630S_paper_mode_runtime_guardrail.py"
    base_report = _run_json_tool(root, "tools/check_4B436630S_paper_mode_runtime_guardrail.py") if base_checker.exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30t_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30s_checker_ok": bool(base_report.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_source_30s_ok": bool(probe.get("source_30s_ok")),
        "module_probe_multi_cycle_soak_ok": bool(probe.get("multi_cycle_soak_ok")),
        "module_probe_cap_continuity_ok": bool(probe.get("cap_continuity_ok")),
        "module_probe_kill_switch_continuity_ok": bool(probe.get("kill_switch_continuity_ok")),
        "module_probe_no_exchange_submit_ok": bool(probe.get("no_exchange_submit_ok")),
        "module_probe_no_live_real_ok": bool(probe.get("no_live_real_ok")),
        "exchange_submit_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_blocked": bool(probe.get("live_real_blocked")),
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "base_30s_checker": base_report,
        "module_probe": probe,
        "read_only": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "network_submit_attempted": False,
        "approved_for_live_real": False,
    }
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
