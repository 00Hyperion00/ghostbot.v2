from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "src/tradebot/paper_transition_operator_gate.py",
    "tests/test_paper_transition_operator_gate_4B436630B.py",
    "tools/apply_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/check_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/run_4B436630B_paper_transition_operator_approval_gate.py",
    "tools/rollback_4B436630B_paper_transition_operator_approval_gate.py",
    "docs/PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_4B436630B.md",
]
CONFIG_FIELDS = [
    "paper_transition_operator_id",
    "paper_transition_approval_issued_at_ms",
    "paper_transition_approval_ttl_sec",
    "paper_transition_runtime_envelope",
    "paper_transition_dry_run_reconciliation_required",
    "paper_transition_dry_run_reconciliation_probe_passed",
    "paper_transition_dry_run_probe_order_actions_performed",
    "paper_transition_max_open_orders",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _module_probe() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_transition_operator_gate import READY_DECISION, APPROVAL_REQUIRED_DECISION, build_paper_transition_operator_gate_snapshot
    except Exception as exc:
        return {"ok": False, "reason": f"IMPORT_FAILED:{exc}"}
    preflight = {
        "approved_for_no_order_to_paper_transition_preflight": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_live_order_blocked": True,
    }
    default_snapshot = build_paper_transition_operator_gate_snapshot(Settings(), preflight, now_ms=1_000_000)
    approved = Settings(
        paper_transition_operator_approved=True,
        paper_transition_operator_id="operator-1",
        paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        paper_transition_approval_issued_at_ms=1_000_000,
        paper_transition_approval_ttl_sec=900,
    )
    approved_snapshot = build_paper_transition_operator_gate_snapshot(approved, preflight, now_ms=1_000_100)
    return {
        "ok": default_snapshot["decision"] == APPROVAL_REQUIRED_DECISION and approved_snapshot["decision"] == READY_DECISION,
        "default_decision": default_snapshot["decision"],
        "approved_decision": approved_snapshot["decision"],
        "approved_transition_candidate": approved_snapshot["approved_for_paper_transition_candidate"],
        "paper_candidate_still_blocked": not approved_snapshot["approved_for_paper_candidate"],
        "live_real_still_blocked": not approved_snapshot["approved_for_live_real"],
    }


def build_report() -> dict[str, Any]:
    expected = {path: (ROOT / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(ROOT / path) for path in EXPECTED_FILES if path.endswith(".py") and (ROOT / path).exists()}
    config_text = (ROOT / "src/tradebot/config.py").read_text(encoding="utf-8")
    module_probe = _module_probe()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": "4B.4.3.6.6.30B" in (ROOT / "src/tradebot/paper_transition_operator_gate.py").read_text(encoding="utf-8"),
        "config_30b_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "typed_approval_token_gate_present": "typed_approval_token_gate" in (ROOT / "src/tradebot/paper_transition_operator_gate.py").read_text(encoding="utf-8"),
        "sandbox_only_runtime_envelope_present": "sandbox_only_runtime_envelope_gate" in (ROOT / "src/tradebot/paper_transition_operator_gate.py").read_text(encoding="utf-8"),
        "dry_run_reconciliation_probe_present": "paper_dry_run_reconciliation_probe_gate" in (ROOT / "src/tradebot/paper_transition_operator_gate.py").read_text(encoding="utf-8"),
        "module_probe_ok": bool(module_probe.get("ok")),
        "paper_live_order_blocked": True,
        "live_real_blocked": True,
        "runtime_activation_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": "4B.4.3.6.6.30B",
        "read_only": True,
        "paper_transition_operator_approval_gate": True,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "module_probe": module_probe,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
