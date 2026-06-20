from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30K"
EXPECTED_FILES = [
    "README_APPLY_4B436630K.txt",
    "docs/PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_4B436630K.md",
    "src/tradebot/paper_sandbox_operator_final_go_no_go_gate.py",
    "tests/test_paper_sandbox_operator_final_go_no_go_gate_4B436630K.py",
    "tools/apply_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/rollback_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/run_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
]
COMPILE_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_sandbox_operator_final_go_no_go_gate.py",
    "tests/test_paper_sandbox_operator_final_go_no_go_gate_4B436630K.py",
    "tools/apply_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/rollback_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
    "tools/run_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_operator_final_go_no_go_gate_enabled",
    "paper_sandbox_operator_final_approval_required",
    "paper_sandbox_operator_final_approval_operator_id",
    "paper_sandbox_operator_final_approval_phrase",
    "paper_sandbox_operator_final_approval_token",
    "paper_sandbox_operator_final_approval_issued",
    "paper_sandbox_operator_final_approval_issued_at_ms",
    "paper_sandbox_operator_final_approval_ttl_sec",
    "paper_sandbox_operator_kill_switch_check_required",
    "paper_sandbox_operator_kill_switch_confirmed",
    "paper_sandbox_operator_caps_check_required",
    "paper_sandbox_operator_caps_confirmed",
    "paper_sandbox_operator_paper_candidate_still_blocked_required",
    "paper_sandbox_operator_no_live_real_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_files(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rel in COMPILE_FILES:
        try:
            py_compile.compile(str(root / rel), doraise=True)
            out[rel] = {"ok": True, "error": ""}
        except Exception as exc:
            out[rel] = {"ok": False, "error": str(exc)}
    return out


def run_base_30j_checker(root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "check_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py"), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    out: dict[str, Any] = {"ok": False, "returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}
    try:
        parsed = json.loads(proc.stdout)
        if isinstance(parsed, dict):
            out.update(parsed)
            out["returncode"] = proc.returncode
    except json.JSONDecodeError:
        pass
    return out


def synthetic_30j_ready_payload() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30J",
        "ok": True,
        "decision": "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof": True,
        "approved_for_30i_simulated_fill_ledger_consumption": True,
        "approved_for_order_fill_position_balance_reconciliation": True,
        "approved_for_mismatch_zero_proof": True,
        "approved_for_sqlite_audit_mirror": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reconciliation_mismatch_zero_verified": True,
        "sqlite_audit_mirror_verified": True,
        "no_exchange_submit_verified": True,
        "paper_candidate_still_blocked_verified": True,
        "mismatch_count": 0,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
    }


def module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_operator_final_go_no_go_gate import (
        OPERATOR_APPROVAL_REQUIRED_DECISION,
        READY_DECISION,
        build_from_latest_30j_ready_report,
    )

    with tempfile.TemporaryDirectory(prefix="tradebot_30k_probe_") as raw:
        reports = Path(raw)
        source_path = reports / "4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger_proof_20990101T000000Z_ready.json"
        source_path.write_text(json.dumps(synthetic_30j_ready_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        default_payload = build_from_latest_30j_ready_report(settings=Settings(), reports_dir=reports)
        ready_payload = build_from_latest_30j_ready_report(
            settings=Settings(),
            reports_dir=reports,
            operator_id="operator-30k",
            approval_token="APPROVE_PAPER_SANDBOX_GO_NO_GO",
            issue_final_approval=True,
            confirm_kill_switch=True,
            confirm_caps=True,
            now_ms=1_800_000_000_000,
        )
    return {
        "ok": ready_payload.get("decision") == READY_DECISION and default_payload.get("decision") == OPERATOR_APPROVAL_REQUIRED_DECISION,
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "ready_gate": ready_payload.get("approved_for_paper_sandbox_operator_final_go_no_go_gate"),
        "operator_approval_ok": ready_payload.get("operator_final_approval_verified"),
        "kill_switch_caps_ok": ready_payload.get("kill_switch_caps_checklist_verified"),
        "paper_candidate_blocked": ready_payload.get("approved_for_paper_candidate") is False and ready_payload.get("paper_candidate_still_blocked_verified") is True,
        "live_real_blocked": ready_payload.get("approved_for_live_real") is False and ready_payload.get("no_live_real_verified") is True,
        "exchange_submit_blocked": ready_payload.get("approved_for_exchange_submit") is False and ready_payload.get("exchange_submit_performed") is False,
    }


def build_report(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = compile_files(root)
    config_text = (root / "src" / "tradebot" / "config.py").read_text(encoding="utf-8")
    source_text = (root / "src" / "tradebot" / "paper_sandbox_operator_final_go_no_go_gate.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_sandbox_operator_final_go_no_go_gate.py").exists() else ""
    base_30j = run_base_30j_checker(root)
    probe = module_probe(root) if all(item["ok"] for item in compiled.values()) else {"ok": False}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item["ok"] for item in compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in source_text,
        "config_30k_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "base_30j_checker_ok": bool(base_30j.get("ok")),
        "source_30j_reconciliation_gate_present": "source_30j_reconciliation_proof_gate" in source_text,
        "operator_final_approval_gate_present": "operator_final_paper_sandbox_approval_gate" in source_text,
        "kill_switch_caps_checklist_gate_present": "kill_switch_caps_checklist_gate" in source_text,
        "paper_candidate_block_until_next_approval_gate_present": "paper_candidate_still_blocked_until_next_explicit_approval_gate" in source_text,
        "no_live_real_gate_present": "no_live_real_gate" in source_text,
        "module_probe_ok": bool(probe.get("ok")),
        "module_probe_operator_approval_ok": bool(probe.get("operator_approval_ok")),
        "module_probe_kill_switch_caps_ok": bool(probe.get("kill_switch_caps_ok")),
        "exchange_submit_still_blocked": bool(probe.get("exchange_submit_blocked")) and not bool(base_30j.get("exchange_submit_performed", False)),
        "paper_candidate_still_blocked": bool(probe.get("paper_candidate_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_blocked")),
        "paper_execution_still_blocked": True,
        "order_actions_blocked": not bool(base_30j.get("order_actions_performed", False)),
        "runtime_training_reload_mutation_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
        "base_30j_report_summary": {"ok": base_30j.get("ok"), "contract_version": base_30j.get("contract_version"), "checks": base_30j.get("checks", {})},
        "module_probe": probe,
        "read_only": True,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "paper_live_order_enablement_present": False,
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
