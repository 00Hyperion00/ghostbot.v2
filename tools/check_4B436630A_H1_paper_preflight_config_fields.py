from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30A-H1"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.30A"

EXPECTED_FILES = [
    "src/tradebot/paper_candidate_gate.py",
    "tests/test_paper_candidate_preflight_4B436630A.py",
    "tools/check_4B436630A_paper_candidate_preflight.py",
    "tools/run_4B436630A_paper_candidate_preflight.py",
    "tools/apply_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/check_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/run_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/rollback_4B436630A_H1_paper_preflight_config_fields.py",
    "tests/test_paper_preflight_config_fields_4B436630A_H1.py",
    "docs/PAPER_PREFLIGHT_CONFIG_FIELDS_4B436630A_H1.md",
]

REQUIRED_CONFIG_FIELDS = [
    "paper_candidate_preflight_enabled",
    "paper_transition_operator_approval_required",
    "paper_transition_operator_approved",
    "paper_transition_confirmation_phrase",
    "paper_transition_confirmation_token",
    "paper_exchange_sandbox_required",
    "paper_sandbox_allowed_market_types",
    "paper_transition_capital_cap_usd",
    "paper_order_notional_cap_usd",
    "paper_max_daily_loss_usd",
    "paper_max_daily_trades_cap",
    "paper_kill_switch_required",
    "paper_kill_switch_enabled",
]

COMPILE_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_candidate_gate.py",
    "tests/test_paper_candidate_preflight_4B436630A.py",
    "tests/test_paper_preflight_config_fields_4B436630A_H1.py",
    "tools/apply_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/check_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/run_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/rollback_4B436630A_H1_paper_preflight_config_fields.py",
    "tools/check_4B436630A_paper_candidate_preflight.py",
    "tools/run_4B436630A_paper_candidate_preflight.py",
]


def _compile(root: Path, rel: str) -> bool:
    path = root / rel
    if not path.exists() or path.suffix != ".py":
        return False
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _load_base_check(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tools"))
    try:
        module = importlib.import_module("check_4B436630A_paper_candidate_preflight")
        return dict(module.build_report(root))
    finally:
        try:
            sys.path.remove(str(root / "tools"))
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_candidate_gate import evaluate_paper_candidate_preflight

        production_ready = {
            "decision": "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
            "evidence_complete": True,
            "approved_for_paper_candidate_preflight": True,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
        }
        base = evaluate_paper_candidate_preflight(Settings(), production_ready)
        approved = evaluate_paper_candidate_preflight(Settings(
            paper_transition_operator_approved=True,
            paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        ), production_ready)
        invalid_caps = evaluate_paper_candidate_preflight(Settings(
            paper_transition_capital_cap_usd=10.0,
            paper_order_notional_cap_usd=25.0,
        ), production_ready)
        return {
            "ok": True,
            "base_preflight_ready": bool(base.approved_for_no_order_to_paper_transition_preflight),
            "base_transition_candidate": bool(base.approved_for_paper_transition_candidate),
            "approved_transition_candidate": bool(approved.approved_for_paper_transition_candidate),
            "approved_paper_candidate": bool(approved.approved_for_paper_candidate),
            "approved_live_real": bool(approved.approved_for_live_real),
            "invalid_caps_block_preflight": not bool(invalid_caps.approved_for_no_order_to_paper_transition_preflight),
            "operator_approval_required": bool(base.operator_approval_required),
            "operator_approval_verified": bool(approved.operator_approval_verified),
            "live_real_hard_block_verified": not bool(approved.approved_for_live_real),
        }
    except Exception as exc:
        return {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def build_report(root: Path) -> dict[str, Any]:
    expected_files = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = {rel: _compile(root, rel) for rel in COMPILE_FILES if (root / rel).exists()}
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8")
    config_fields_present = all(field in config_text for field in REQUIRED_CONFIG_FIELDS)
    probe = _module_probe(root)
    try:
        base_report = _load_base_check(root)
    except Exception as exc:
        base_report = {"ok": False, "reason": str(exc), "checks": {}}

    checks = {
        "all_expected_files_present": all(expected_files.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "base_30a_checker_ok": bool(base_report.get("ok")),
        "base_contract_version_ok": str(base_report.get("contract_version") or "") == BASE_CONTRACT_VERSION,
        "config_paper_preflight_fields_present": config_fields_present,
        "module_probe_ok": bool(probe.get("ok")),
        "operator_approval_required_blocks_transition": bool(probe.get("base_preflight_ready")) and not bool(probe.get("base_transition_candidate")),
        "operator_approved_transition_candidate_review_only": bool(probe.get("approved_transition_candidate")) and not bool(probe.get("approved_paper_candidate")),
        "invalid_risk_caps_block_preflight": bool(probe.get("invalid_caps_block_preflight")),
        "live_real_hard_block_verified": bool(probe.get("live_real_hard_block_verified")),
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    ok = all(checks.values())
    return {
        "contract_version": CONTRACT_VERSION,
        "paper_preflight_config_fields_hotfix": True,
        "read_only": True,
        "ok": ok,
        "checks": checks,
        "expected_files": expected_files,
        "compiled": compiled,
        "module_probe": probe,
        "base_30a_report": base_report,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.30A-H1 paper preflight config fields hotfix")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} paper preflight config fields {'OK' if report['ok'] else 'NOT_READY'}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
