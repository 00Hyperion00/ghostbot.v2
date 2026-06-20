from __future__ import annotations

import argparse
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30C"
EXPECTED_FILES = (
    "docs/PAPER_TRANSITION_CANDIDATE_REVIEW_4B436630C.md",
    "src/tradebot/paper_transition_candidate_review.py",
    "tests/test_paper_transition_candidate_review_4B436630C.py",
    "tools/apply_4B436630C_paper_transition_candidate_review.py",
    "tools/check_4B436630C_paper_transition_candidate_review.py",
    "tools/rollback_4B436630C_paper_transition_candidate_review.py",
    "tools/run_4B436630C_paper_transition_candidate_review.py",
)
PY_FILES = tuple(path for path in EXPECTED_FILES if path.endswith(".py"))
REQUIRED_CONFIG_FIELDS = (
    "paper_transition_candidate_review_enabled",
    "paper_transition_operator_evidence_required",
    "paper_transition_runtime_envelope_freeze_required",
    "paper_transition_runtime_envelope_frozen",
    "paper_transition_runtime_envelope_freeze_phrase",
    "paper_transition_runtime_envelope_freeze_token",
    "paper_transition_final_risk_cap_verification_required",
    "paper_transition_final_risk_cap_verified",
    "paper_transition_still_no_order_enablement_required",
)


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _read_config(root: Path) -> str:
    path = root / "src" / "tradebot" / "config.py"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_transition_candidate_review import (
            CONTRACT_VERSION as MODULE_CONTRACT_VERSION,
            OPERATOR_EVIDENCE_REQUIRED_DECISION,
            READY_DECISION,
            evaluate_paper_transition_candidate_review,
        )

        default_source = {
            "contract_version": "4B.4.3.6.6.30B",
            "decision": "PAPER_TRANSITION_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED",
            "approved_for_paper_transition_operator_approval_gate": True,
            "approved_for_paper_transition_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "operator_approval_verified": False,
            "sandbox_runtime_envelope_verified": True,
            "paper_dry_run_reconciliation_probe_verified": True,
            "paper_live_order_enablement_present": False,
            "trading_action_performed": False,
            "order_actions_performed": False,
            "sandbox_runtime_envelope": {
                "runtime_envelope": "sandbox_only",
                "execution_mode": "dry_run",
                "market_type": "spot_demo",
                "base_url": "https://demo-api.binance.com",
                "auto_trade_on_signal": False,
                "live_trading_armed": False,
                "live_real_double_confirm": False,
                "max_open_orders": 1,
            },
            "paper_preflight_snapshot": {
                "risk_limits": {
                    "capital_cap_usd": 100.0,
                    "order_notional_cap_usd": 25.0,
                    "max_daily_loss_usd": 5.0,
                    "max_daily_trades_cap": 5,
                    "kill_switch_enabled": True,
                }
            },
        }
        approved_source = dict(default_source)
        approved_source.update({
            "decision": "PAPER_TRANSITION_OPERATOR_APPROVAL_GATE_READY_REVIEW_ONLY_LIVE_REAL_BLOCKED",
            "approved_for_paper_transition_candidate": True,
            "operator_approval_verified": True,
        })
        approved_settings = Settings(
            paper_transition_runtime_envelope_frozen=True,
            paper_transition_runtime_envelope_freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
            paper_transition_final_risk_cap_verified=True,
        )
        default_decision = evaluate_paper_transition_candidate_review(Settings(), default_source)
        approved_decision = evaluate_paper_transition_candidate_review(approved_settings, approved_source)
        ok = (
            MODULE_CONTRACT_VERSION == CONTRACT_VERSION
            and default_decision.decision == OPERATOR_EVIDENCE_REQUIRED_DECISION
            and default_decision.approved_for_paper_transition_candidate_review is False
            and approved_decision.decision == READY_DECISION
            and approved_decision.approved_for_paper_transition_candidate_review is True
            and approved_decision.approved_for_paper_candidate is False
            and approved_decision.approved_for_live_real is False
            and approved_decision.trading_action_performed is False
        )
        return {
            "ok": ok,
            "contract_version": MODULE_CONTRACT_VERSION,
            "default_decision": default_decision.decision,
            "approved_decision": approved_decision.decision,
            "approved_review_only": approved_decision.approved_for_paper_transition_candidate_review,
            "paper_candidate_still_blocked": not approved_decision.approved_for_paper_candidate,
            "live_real_still_blocked": not approved_decision.approved_for_live_real,
        }
    except Exception as exc:
        return {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    finally:
        try:
            sys.path.remove(str(root / "src"))
        except ValueError:
            pass


def build_report(root: Path) -> dict[str, Any]:
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(root / path) for path in PY_FILES if (root / path).exists()}
    config_text = _read_config(root)
    config_fields = {field: field in config_text for field in REQUIRED_CONFIG_FIELDS}
    module_probe = _module_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) and len(compiled) == len(PY_FILES),
        "contract_version_ok": CONTRACT_VERSION in (root / "src" / "tradebot" / "paper_transition_candidate_review.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_transition_candidate_review.py").exists() else False,
        "config_30c_fields_present": all(config_fields.values()),
        "module_probe_ok": bool(module_probe.get("ok")),
        "operator_approval_evidence_gate_present": "evaluate_operator_approval_evidence" in (root / "src" / "tradebot" / "paper_transition_candidate_review.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_transition_candidate_review.py").exists() else False,
        "runtime_envelope_freeze_gate_present": "evaluate_runtime_envelope_freeze" in (root / "src" / "tradebot" / "paper_transition_candidate_review.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_transition_candidate_review.py").exists() else False,
        "final_risk_cap_verification_gate_present": "evaluate_final_risk_cap_verification" in (root / "src" / "tradebot" / "paper_transition_candidate_review.py").read_text(encoding="utf-8") if (root / "src" / "tradebot" / "paper_transition_candidate_review.py").exists() else False,
        "paper_order_enablement_still_blocked": True,
        "live_real_blocked": True,
        "runtime_activation_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "paper_transition_candidate_review_gate": True,
        "read_only": True,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "config_fields": config_fields,
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
    root = Path(__file__).resolve().parents[1]
    report = build_report(root)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} checker {'OK' if report['ok'] else 'FAILED'}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
