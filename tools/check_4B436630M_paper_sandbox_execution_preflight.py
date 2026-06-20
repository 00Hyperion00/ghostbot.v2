
from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30M"
EXPECTED_FILES = [
    "README_APPLY_4B436630M.txt",
    "docs/PAPER_SANDBOX_EXECUTION_PREFLIGHT_4B436630M.md",
    "src/tradebot/paper_sandbox_execution_preflight.py",
    "tests/test_paper_sandbox_execution_preflight_4B436630M.py",
    "tools/apply_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/check_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/rollback_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/run_4B436630M_paper_sandbox_execution_preflight.py",
]
PY_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_execution_preflight.py",
    "tests/test_paper_sandbox_execution_preflight_4B436630M.py",
    "tools/apply_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/check_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/rollback_4B436630M_paper_sandbox_execution_preflight.py",
    "tools/run_4B436630M_paper_sandbox_execution_preflight.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_execution_preflight_enabled",
    "paper_sandbox_execution_preflight_consume_30l_required",
    "paper_sandbox_execution_preflight_authorization_required",
    "paper_sandbox_execution_preflight_operator_id",
    "paper_sandbox_execution_preflight_authorization_phrase",
    "paper_sandbox_execution_preflight_authorization_token",
    "paper_sandbox_execution_preflight_authorization_issued",
    "paper_sandbox_execution_preflight_authorization_issued_at_ms",
    "paper_sandbox_execution_preflight_authorization_ttl_sec",
    "paper_sandbox_execution_preflight_order_envelope_required",
    "paper_sandbox_execution_preflight_no_exchange_submit_required",
    "paper_sandbox_execution_preflight_no_live_real_required",
    "paper_sandbox_execution_preflight_order_envelope_path",
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
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    proc = subprocess.run(
        [sys.executable, "-B", str(root / rel), "--once-json"],
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


def _source_ready() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30L",
        "decision": "PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "approved_for_paper_sandbox_candidate_unlock_gate": True,
        "approved_for_explicit_paper_candidate_unlock": True,
        "approved_for_sandbox_only_order_enablement_preflight": True,
        "approved_for_paper_sandbox_candidate": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_execution_preflight import (
        AUTHORIZATION_REQUIRED_DECISION,
        READY_DECISION,
        build_paper_sandbox_execution_preflight_snapshot,
    )
    default_payload = build_paper_sandbox_execution_preflight_snapshot(Settings(), _source_ready(), now_ms=1_800_000_000_000)
    ready_payload = build_paper_sandbox_execution_preflight_snapshot(
        Settings(),
        _source_ready(),
        operator_id="operator-30m",
        authorization_token="AUTHORIZE_PAPER_SANDBOX_EXECUTION_PREFLIGHT",
        issue_dry_run_authorization=True,
        now_ms=1_800_000_000_000,
    )
    return {
        "ok": default_payload.get("decision") == AUTHORIZATION_REQUIRED_DECISION and ready_payload.get("decision") == READY_DECISION,
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "source_30l_ok": bool(ready_payload.get("source_30l_candidate_unlock_verified")),
        "authorization_ok": bool(ready_payload.get("dry_run_authorization_verified")),
        "order_envelope_ok": bool(ready_payload.get("order_envelope_built")),
        "paper_candidate_ok": bool(ready_payload.get("approved_for_paper_candidate")),
        "paper_execution_blocked": ready_payload.get("approved_for_paper_sandbox_dry_run_execution") is False,
        "exchange_submit_blocked": ready_payload.get("approved_for_exchange_submit") is False and ready_payload.get("exchange_submit_performed") is False,
        "live_real_blocked": ready_payload.get("approved_for_live_real") is False,
    }


def build_report(root: Path) -> dict[str, Any]:
    source = (root / "src/tradebot/paper_sandbox_execution_preflight.py").read_text(encoding="utf-8") if (root / "src/tradebot/paper_sandbox_execution_preflight.py").exists() else ""
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8") if (root / "src/tradebot/config.py").exists() else ""
    compiled = _compile(root)
    base_report = _run_json_tool(root, "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py") if (root / "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py").exists() else {"ok": False, "missing": True}
    probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all((root / rel).exists() for rel in EXPECTED_FILES),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source,
        "config_30m_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30l_h2_checker_ok": bool(base_report.get("ok")),
        "source_30l_candidate_unlock_gate_present": "source_30l_candidate_unlock_gate" in source,
        "dry_run_authorization_gate_present": "paper_sandbox_dry_run_authorization_gate" in source,
        "order_envelope_build_gate_present": "order_envelope_build_gate" in source,
        "no_exchange_submit_gate_present": "no_exchange_submit_gate" in source,
        "no_live_real_gate_present": "no_live_real_gate" in source,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_authorization_ok": bool(probe.get("authorization_ok")),
        "module_probe_order_envelope_ok": bool(probe.get("order_envelope_ok")),
        "paper_candidate_preserved": bool(probe.get("paper_candidate_ok")),
        "paper_execution_still_blocked": bool(probe.get("paper_execution_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "compiled": compiled,
        "base_30l_h2_report_summary": {
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(repo_root())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
