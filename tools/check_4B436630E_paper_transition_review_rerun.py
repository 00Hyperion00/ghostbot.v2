from __future__ import annotations

import argparse
import json
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30E"
EXPECTED_FILES = (
    "README_APPLY_4B436630E.txt",
    "docs/PAPER_TRANSITION_REVIEW_RERUN_4B436630E.md",
    "src/tradebot/paper_transition_review_rerun.py",
    "tests/test_paper_transition_review_rerun_4B436630E.py",
    "tools/apply_4B436630E_paper_transition_review_rerun.py",
    "tools/check_4B436630E_paper_transition_review_rerun.py",
    "tools/run_4B436630E_paper_transition_review_rerun.py",
    "tools/rollback_4B436630E_paper_transition_review_rerun.py",
)
BASE_FILES = (
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "src/tradebot/paper_transition_candidate_review.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
)
PY_FILES = tuple(path for path in (*EXPECTED_FILES, *BASE_FILES) if path.endswith(".py"))
REQUIRED_CONFIG_FIELDS = (
    "paper_transition_review_rerun_enabled",
    "paper_transition_review_rerun_consume_30d_ready_required",
    "paper_transition_review_rerun_require_30c_ready",
    "paper_transition_review_rerun_still_no_order_enablement_required",
    "paper_transition_review_rerun_evidence_report_required",
)


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _compile(root: Path, rel: str) -> bool:
    path = root / rel
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _read(root: Path, rel: str) -> str:
    path = root / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _run_base_30d_checker(root: Path) -> dict[str, Any]:
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


def _module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.paper_transition_approval_evidence_capture import build_from_operator_inputs, write_report_bundle as write_30d_report
        from tradebot.paper_transition_review_rerun import (
            EVIDENCE_REQUIRED_DECISION,
            READY_DECISION,
            build_from_latest_30d_ready_report,
            write_report_bundle as write_30e_report,
        )
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            default_payload = build_from_latest_30d_ready_report(reports)
            ready_30d = build_from_operator_inputs(
                operator_id="operator-30d",
                confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
                freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
                issue_approval=True,
                freeze_runtime_envelope=True,
                verify_final_risk_cap=True,
                reports_dir=reports,
                now_ms=1_800_000_000_000,
            )
            ready_path, _ = write_30d_report(ready_30d, reports)
            ready_payload = build_from_latest_30d_ready_report(reports)
            json1, _ = write_30e_report(default_payload, reports)
            json2, _ = write_30e_report(ready_payload, reports)
            collision_guard_ok = json1.name != json2.name and json1.exists() and json2.exists()
        ok = (
            default_payload["decision"] == EVIDENCE_REQUIRED_DECISION
            and ready_path.name.endswith("_ready.json")
            and ready_payload["decision"] == READY_DECISION
            and ready_payload["approved_for_paper_transition_review_rerun"] is True
            and ready_payload["approved_for_paper_transition_candidate_review"] is True
            and ready_payload["approved_for_paper_transition_candidate"] is False
            and ready_payload["approved_for_paper_candidate"] is False
            and ready_payload["approved_for_live_real"] is False
            and ready_payload["trading_action_performed"] is False
            and ready_payload["paper_order_enablement_still_blocked"] is True
            and collision_guard_ok
        )
        return {
            "ok": ok,
            "default_decision": default_payload["decision"],
            "ready_decision": ready_payload["decision"],
            "ready_review_rerun": ready_payload["approved_for_paper_transition_review_rerun"],
            "paper_transition_candidate_still_blocked": not ready_payload["approved_for_paper_transition_candidate"],
            "paper_candidate_still_blocked": not ready_payload["approved_for_paper_candidate"],
            "live_real_still_blocked": not ready_payload["approved_for_live_real"],
            "order_actions_blocked": not ready_payload["trading_action_performed"],
            "collision_guard_ok": collision_guard_ok,
        }
    except Exception as exc:
        return {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}


def build_report(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base_files = {rel: (root / rel).exists() for rel in BASE_FILES}
    compiled = {rel: _compile(root, rel) for rel in PY_FILES if (root / rel).exists()}
    config_text = _read(root, "src/tradebot/config.py")
    config_fields = {field: field in config_text for field in REQUIRED_CONFIG_FIELDS}
    source_text = _read(root, "src/tradebot/paper_transition_review_rerun.py")
    base_30d_report = _run_base_30d_checker(root)
    module_probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base_files.values()),
        "all_py_compile_ok": all(compiled.values()) and len(compiled) == len(PY_FILES),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30e_fields_present": all(config_fields.values()),
        "base_30d_checker_ok": bool(base_30d_report.get("ok")),
        "source_30d_ready_evidence_gate_present": "evaluate_30d_ready_evidence" in source_text,
        "source_30c_review_rerun_gate_present": "evaluate_30c_review_rerun" in source_text,
        "latest_30d_ready_report_selector_present": "latest_30d_ready_report" in source_text and "*_ready" in source_text,
        "report_collision_guard_present": "_unique_report_path" in source_text,
        "module_probe_ok": bool(module_probe.get("ok")),
        "paper_transition_candidate_still_blocked": bool(module_probe.get("paper_transition_candidate_still_blocked")),
        "paper_candidate_still_blocked": bool(module_probe.get("paper_candidate_still_blocked")),
        "live_real_still_blocked": bool(module_probe.get("live_real_still_blocked")),
        "order_actions_blocked": bool(module_probe.get("order_actions_blocked")),
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "paper_transition_review_rerun_gate": True,
        "read_only": True,
        "checks": checks,
        "expected_files": expected,
        "base_files": base_files,
        "compiled": compiled,
        "config_fields": config_fields,
        "base_30d_report": base_30d_report,
        "module_probe": module_probe,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(repo_root())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker {'OK' if report['ok'] else 'FAILED'}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
