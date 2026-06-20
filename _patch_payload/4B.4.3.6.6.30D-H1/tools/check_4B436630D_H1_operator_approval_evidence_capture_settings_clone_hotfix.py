from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30D-H1"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.30D"
EXPECTED_FILES = [
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D_H1.md",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py",
    "tools/apply_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
    "tools/check_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
    "tools/rollback_4B436630D_H1_operator_approval_evidence_capture_settings_clone_hotfix.py",
]
BASE_FILES = [
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D.py",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
]
PY_FILES = [item for item in [*EXPECTED_FILES, *BASE_FILES] if item.endswith(".py")]
BAD_SETTINGS_KWARG_LINE = '            "paper_live_order_enablement_present": False,\n'


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_py(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def _settings_clone_block(source: str) -> str:
    start = source.find("def build_approval_capture_settings(")
    end = source.find("def evaluate_typed_approval_issuance", start)
    if start < 0 or end < 0:
        return ""
    return source[start:end]


def run_base_30d_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630D_operator_approval_evidence_capture.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30D_CHECKER_MISSING"}
    proc = subprocess.run(
        [sys.executable, str(checker), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"ok": False, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    payload["returncode"] = proc.returncode
    return payload


def run_check(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    compiled = compile_py(root)
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base_expected = {rel: (root / rel).exists() for rel in BASE_FILES}
    source_path = root / "src" / "tradebot" / "paper_transition_approval_evidence_capture.py"
    source = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    settings_clone_block = _settings_clone_block(source)
    base_report = run_base_30d_checker(root)
    checks: dict[str, bool] = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base_expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "settings_clone_unsupported_kwarg_removed": BAD_SETTINGS_KWARG_LINE not in settings_clone_block,
        "base_30d_checker_ok": bool(base_report.get("ok", False)),
        "base_30d_module_probe_ok": bool(base_report.get("checks", {}).get("module_probe_ok", False)),
        "default_capture_input_required": False,
        "explicit_evidence_capture_ready": False,
        "paper_transition_candidate_still_blocked": False,
        "paper_candidate_still_blocked": False,
        "live_real_still_blocked": False,
        "order_actions_blocked": False,
        "runtime_activation_blocked": False,
        "training_reload_blocked": False,
    }
    probe: dict[str, Any] = {"ok": False}
    try:
        from tradebot.paper_transition_approval_evidence_capture import (
            INPUT_REQUIRED_DECISION,
            READY_DECISION,
            build_from_operator_inputs,
        )
        now = 1_800_000_000_000
        default_payload = build_from_operator_inputs(now_ms=now)
        approved_payload = build_from_operator_inputs(
            operator_id="operator-30d",
            confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
            freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
            issue_approval=True,
            freeze_runtime_envelope=True,
            verify_final_risk_cap=True,
            now_ms=now,
        )
        checks["default_capture_input_required"] = default_payload.get("decision") == INPUT_REQUIRED_DECISION
        checks["explicit_evidence_capture_ready"] = approved_payload.get("decision") == READY_DECISION and bool(approved_payload.get("approved_for_operator_approval_evidence_capture"))
        checks["paper_transition_candidate_still_blocked"] = not bool(approved_payload.get("approved_for_paper_transition_candidate"))
        checks["paper_candidate_still_blocked"] = not bool(approved_payload.get("approved_for_paper_candidate"))
        checks["live_real_still_blocked"] = not bool(approved_payload.get("approved_for_live_real"))
        checks["order_actions_blocked"] = not bool(approved_payload.get("trading_action_performed")) and not bool(approved_payload.get("order_actions_performed")) and not bool(approved_payload.get("paper_live_order_enablement_present"))
        checks["runtime_activation_blocked"] = bool(approved_payload.get("runtime_activation_blocked"))
        checks["training_reload_blocked"] = bool(approved_payload.get("training_reload_blocked"))
        probe = {
            "ok": all([
                checks["default_capture_input_required"],
                checks["explicit_evidence_capture_ready"],
                checks["paper_transition_candidate_still_blocked"],
                checks["paper_candidate_still_blocked"],
                checks["live_real_still_blocked"],
                checks["order_actions_blocked"],
            ]),
            "default_decision": default_payload.get("decision"),
            "approved_decision": approved_payload.get("decision"),
            "approved_capture": approved_payload.get("approved_for_operator_approval_evidence_capture"),
            "approved_review_only": approved_payload.get("approved_for_paper_transition_candidate_review"),
            "approved_paper_transition_candidate": approved_payload.get("approved_for_paper_transition_candidate"),
            "approved_paper_candidate": approved_payload.get("approved_for_paper_candidate"),
            "approved_live_real": approved_payload.get("approved_for_live_real"),
        }
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    report = {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": BASE_CONTRACT_VERSION,
        "checks": checks,
        "expected_files": expected,
        "base_expected_files": base_expected,
        "compiled": compiled,
        "base_30d_report": base_report,
        "module_probe": probe,
        "read_only": True,
        "settings_clone_hotfix": True,
        "paper_live_order_enablement_present": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    report = run_check(root)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} settings clone hotfix checker ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
