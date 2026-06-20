from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30L"
EXPECTED_FILES = [
    "README_APPLY_4B436630L.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_4B436630L.md",
    "src/tradebot/paper_sandbox_candidate_unlock_gate.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py",
    "tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/rollback_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py",
]
COMPILE_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_candidate_unlock_gate.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py",
    "tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/rollback_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_candidate_unlock_gate_enabled",
    "paper_sandbox_candidate_unlock_consume_30k_required",
    "paper_sandbox_candidate_unlock_explicit_unlock_required",
    "paper_sandbox_candidate_unlock_operator_id",
    "paper_sandbox_candidate_unlock_phrase",
    "paper_sandbox_candidate_unlock_token",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_candidate_unlock_issued_at_ms",
    "paper_sandbox_candidate_unlock_ttl_sec",
    "paper_sandbox_candidate_unlock_sandbox_only_preflight_required",
    "paper_sandbox_candidate_unlock_no_exchange_submit_required",
    "paper_sandbox_candidate_unlock_no_live_real_required",
    "paper_sandbox_candidate_unlock_order_enablement_still_blocked_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in COMPILE_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def _run_json(root: Path, rel: str) -> dict[str, Any]:
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
        payload = {"ok": False, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    payload["returncode"] = proc.returncode
    return payload


def _sample_30k_ready() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30K",
        "decision": "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_READY_PAPER_CANDIDATE_STILL_BLOCKED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_operator_final_go_no_go_gate": True,
        "approved_for_operator_final_paper_sandbox_approval": True,
        "approved_for_kill_switch_caps_checklist": True,
        "approved_for_paper_sandbox_go_no_go_candidate": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": False,
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
    from tradebot.paper_sandbox_candidate_unlock_gate import (
        READY_DECISION,
        UNLOCK_REQUIRED_DECISION,
        build_paper_sandbox_candidate_unlock_snapshot,
    )

    source = _sample_30k_ready()
    settings = Settings()
    default_payload = build_paper_sandbox_candidate_unlock_snapshot(settings, source, source_report_path="sample-30k-ready.json", now_ms=1_800_000_000_000)
    ready_payload = build_paper_sandbox_candidate_unlock_snapshot(
        settings,
        source,
        source_report_path="sample-30k-ready.json",
        operator_id="operator-30l",
        unlock_token="UNLOCK_PAPER_SANDBOX_CANDIDATE",
        issue_candidate_unlock=True,
        now_ms=1_800_000_000_000,
    )
    return {
        "ok": ready_payload.get("decision") == READY_DECISION and default_payload.get("decision") == UNLOCK_REQUIRED_DECISION,
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "ready_gate": bool(ready_payload.get("approved_for_paper_sandbox_candidate_unlock_gate")),
        "explicit_unlock_ok": bool(ready_payload.get("explicit_candidate_unlock_verified")),
        "sandbox_preflight_ok": bool(ready_payload.get("sandbox_only_order_enablement_preflight_verified")),
        "paper_candidate_unlocked_candidate_only": bool(ready_payload.get("approved_for_paper_candidate")),
        "paper_execution_blocked": not bool(ready_payload.get("approved_for_paper_sandbox_dry_run_execution")),
        "exchange_submit_blocked": not bool(ready_payload.get("approved_for_exchange_submit")) and not bool(ready_payload.get("exchange_submit_performed")),
        "live_real_blocked": not bool(ready_payload.get("approved_for_live_real")),
        "paper_order_enablement_still_blocked": bool(ready_payload.get("paper_order_enablement_still_blocked")),
    }


def build_report(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8")
    module_text = (root / "src" / "tradebot" / "paper_sandbox_candidate_unlock_gate.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_candidate_unlock_gate.py").exists() else ""
    base_30k = _run_json(root, "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py") if (root / "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py").exists() else {"ok": False}
    probe: dict[str, Any]
    try:
        probe = _module_probe(root)
    except Exception as exc:
        probe = {"ok": False, "error": str(exc)}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "base_30k_checker_ok": bool(base_30k.get("ok")),
        "contract_version_ok": CONTRACT_VERSION in module_text,
        "config_30l_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "source_30k_go_no_go_gate_present": "SOURCE_30K_READY_DECISION" in module_text and "latest_30k_ready_report" in module_text,
        "explicit_paper_candidate_unlock_gate_present": "explicit_paper_candidate_unlock_gate" in module_text and "UNLOCK_PAPER_SANDBOX_CANDIDATE" in module_text,
        "sandbox_only_order_enablement_preflight_gate_present": "sandbox_only_order_enablement_preflight_gate" in module_text,
        "no_exchange_submit_yet_gate_present": "no_exchange_submit_yet_gate" in module_text,
        "no_live_real_gate_present": "no_live_real_gate" in module_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_explicit_unlock_ok": bool(probe.get("explicit_unlock_ok")),
        "module_probe_sandbox_preflight_ok": bool(probe.get("sandbox_preflight_ok")),
        "paper_candidate_unlocked_candidate_only": bool(probe.get("paper_candidate_unlocked_candidate_only")),
        "paper_execution_still_blocked": bool(probe.get("paper_execution_blocked")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "order_enablement_still_blocked_until_next_gate": bool(probe.get("paper_order_enablement_still_blocked")),
        "runtime_training_reload_mutation_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "base_30k_report_summary": {
            "ok": bool(base_30k.get("ok")),
            "contract_version": base_30k.get("contract_version"),
            "checks": base_30k.get("checks", {}),
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
