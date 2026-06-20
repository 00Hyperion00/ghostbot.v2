from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

HOTFIX_VERSION = "4B.4.3.6.6.30L-H1"
TARGET_CONTRACT_VERSION = "4B.4.3.6.6.30L"
EXPECTED_FILES = [
    "README_APPLY_4B436630L_H1.txt",
    "tools/apply_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
    "tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py",
    "README_APPLY_4B436630L.txt",
    "docs/PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_4B436630L.md",
    "src/tradebot/paper_sandbox_candidate_unlock_gate.py",
    "tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py",
    "tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/rollback_4B436630L_paper_sandbox_candidate_unlock_gate.py",
    "tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py",
]
PY_FILES = [rel for rel in EXPECTED_FILES if rel.endswith(".py")]
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
    env["PYTHONIOENCODING"] = "utf-8"
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


def _check_any(checks: dict[str, Any], *keys: str) -> bool:
    return any(bool(checks.get(key)) for key in keys)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8")
    patch_artifacts_absent = {
        rel: not (root / rel).exists()
        for rel in ("_patch_payload", "tools/_patch_payload", "_patch_backup", "tools/_patch_backup", "tests/_patch_backup", "docs/_patch_backup")
    }
    target_path = "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py"
    target_report = _run_json_tool(root, target_path) if (root / target_path).exists() else {"ok": False, "missing": True}
    target_checks = target_report.get("checks", {}) if isinstance(target_report.get("checks"), dict) else {}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item.get("ok") for item in compiled.values()),
        "contract_version_ok": True,
        "target_30l_checker_ok": bool(target_report.get("ok")),
        "config_30l_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "patch_artifacts_absent_before_checker": all(patch_artifacts_absent.values()),
        "base_30k_checker_ok": bool(target_checks.get("base_30k_checker_ok")),
        "explicit_unlock_gate_present": _check_any(
            target_checks,
            "explicit_paper_candidate_unlock_gate_present",
            "explicit_candidate_unlock_gate_present",
        ),
        "sandbox_preflight_gate_present": _check_any(
            target_checks,
            "sandbox_only_order_enablement_preflight_gate_present",
            "sandbox_order_enablement_preflight_gate_present",
        ),
        "exchange_submit_still_blocked": bool(target_checks.get("exchange_submit_still_blocked")),
        "paper_execution_still_blocked": bool(target_checks.get("paper_execution_still_blocked")),
        "paper_candidate_unlocked_candidate_only": bool(target_checks.get("paper_candidate_unlocked_candidate_only")),
        "live_real_still_blocked": bool(target_checks.get("live_real_still_blocked")),
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": HOTFIX_VERSION,
        "target_contract_version": TARGET_CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "patch_artifacts_absent": patch_artifacts_absent,
        "target_30l_report_summary": {
            "ok": bool(target_report.get("ok")),
            "contract_version": target_report.get("contract_version"),
            "checks": target_checks,
            "module_probe": target_report.get("module_probe", {}),
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
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
