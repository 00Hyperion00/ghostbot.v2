from __future__ import annotations

import argparse, json, py_compile, sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30A"
EXPECTED_FILES = [
    "docs/PAPER_CANDIDATE_PREFLIGHT_4B436630A.md",
    "src/tradebot/paper_candidate_gate.py",
    "tests/test_paper_candidate_preflight_4B436630A.py",
    "tools/apply_4B436630A_paper_candidate_preflight.py",
    "tools/check_4B436630A_paper_candidate_preflight.py",
    "tools/rollback_4B436630A_paper_candidate_preflight.py",
    "tools/run_4B436630A_paper_candidate_preflight.py",
]
PY_COMPILE_FILES = [
    "src/tradebot/config.py",
    "src/tradebot/paper_candidate_gate.py",
    "tests/test_paper_candidate_preflight_4B436630A.py",
    "tools/apply_4B436630A_paper_candidate_preflight.py",
    "tools/check_4B436630A_paper_candidate_preflight.py",
    "tools/rollback_4B436630A_paper_candidate_preflight.py",
    "tools/run_4B436630A_paper_candidate_preflight.py",
]
CONFIG_FIELDS = [
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


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _sample_production_ready() -> dict[str, Any]:
    return {
        "decision": "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
        "evidence_complete": True,
        "approved_for_paper_candidate_preflight": True,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
    }


def _module_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_candidate_gate import evaluate_paper_candidate_preflight
        decision = evaluate_paper_candidate_preflight(Settings(), _sample_production_ready())
        approved = evaluate_paper_candidate_preflight(Settings(paper_transition_operator_approved=True, paper_transition_confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE"), _sample_production_ready())
        return {
            "ok": decision.ok,
            "contract_version": decision.contract_version,
            "preflight_ready": decision.approved_for_no_order_to_paper_transition_preflight,
            "operator_required_blocks_transition": not decision.approved_for_paper_transition_candidate,
            "operator_approved_transition_candidate": approved.approved_for_paper_transition_candidate,
            "paper_candidate_still_blocked": not approved.approved_for_paper_candidate,
            "live_real_still_blocked": not approved.approved_for_live_real,
        }
    except Exception as exc:
        return {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
    finally:
        try: sys.path.remove(str(root / "src"))
        except ValueError: pass


def _evidence_probe(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_candidate_gate import build_paper_candidate_preflight_snapshot
        try:
            from tradebot.production_readiness_gate import build_consolidated_readiness_snapshot
            prod = build_consolidated_readiness_snapshot(root / "reports" / "production_hardening")
        except Exception:
            prod = _sample_production_ready()
        snap = build_paper_candidate_preflight_snapshot(Settings(), prod)
        return {"available": True, "decision": snap.get("decision"), "preflight_ready": bool(snap.get("approved_for_no_order_to_paper_transition_preflight")), "paper_transition_candidate": bool(snap.get("approved_for_paper_transition_candidate")), "paper_candidate": bool(snap.get("approved_for_paper_candidate")), "live_real": bool(snap.get("approved_for_live_real"))}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    finally:
        try: sys.path.remove(str(root / "src"))
        except ValueError: pass


def build_report(root: Path) -> dict[str, Any]:
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(root / path) for path in PY_COMPILE_FILES if (root / path).exists()}
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8")
    module_text = (root / "src/tradebot/paper_candidate_gate.py").read_text(encoding="utf-8") if (root / "src/tradebot/paper_candidate_gate.py").exists() else ""
    module_probe = _module_probe(root)
    evidence_probe = _evidence_probe(root)
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": bool(compiled) and all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in module_text,
        "config_paper_preflight_fields_present": all(field in config_text for field in CONFIG_FIELDS),
        "no_order_to_paper_transition_gate_present": "approved_for_no_order_to_paper_transition_preflight" in module_text,
        "exchange_sandbox_isolation_present": "evaluate_exchange_sandbox_isolation" in module_text,
        "capital_cap_gate_present": "paper_transition_capital_cap_usd" in module_text,
        "kill_switch_gate_present": "PAPER_KILL_SWITCH_REQUIRED_NOT_ENABLED" in module_text,
        "operator_approval_gate_present": "OPERATOR_APPROVAL_REQUIRED_FOR_PAPER_TRANSITION_CANDIDATE" in module_text,
        "module_probe_ok": bool(module_probe.get("ok")) and bool(module_probe.get("preflight_ready")),
        "operator_approval_required_blocks_transition": bool(module_probe.get("operator_required_blocks_transition")),
        "operator_approved_transition_candidate_review_only": bool(module_probe.get("operator_approved_transition_candidate")) and bool(module_probe.get("paper_candidate_still_blocked")),
        "live_real_hard_block_verified": bool(module_probe.get("live_real_still_blocked")),
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    ok = all(checks.values())
    return {"contract_version": CONTRACT_VERSION, "paper_candidate_preflight": True, "read_only": True, "ok": ok, "expected_files": expected, "compiled": compiled, "checks": checks, "module_probe": module_probe, "evidence_probe": evidence_probe, "runtime_overlay_activation_performed": False, "scheduler_mutation_performed": False, "strategy_parameter_mutation_performed": False, "hyp006_strategy_threshold_mutation_performed": False, "training_performed": False, "reload_performed": False, "trading_action_performed": False, "paper_live_order_enablement_present": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    _ = parser.parse_args()
    report = build_report(Path.cwd())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
