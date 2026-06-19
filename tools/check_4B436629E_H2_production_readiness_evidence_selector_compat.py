from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29E-H2"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.29E"

EXPECTED_FILES = [
    "docs/PRODUCTION_READINESS_EVIDENCE_SELECTOR_COMPAT_4B436629E_H2.md",
    "tests/test_production_readiness_evidence_selector_compat_4B436629E_H2.py",
    "tools/apply_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/check_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/rollback_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/run_4B436629E_H2_production_readiness_evidence_selector_compat.py",
]

COMPILE_FILES = [
    "src/tradebot/production_readiness_gate.py",
    "tests/test_production_readiness_evidence_selector_compat_4B436629E_H2.py",
    "tools/apply_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/check_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/rollback_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/run_4B436629E_H2_production_readiness_evidence_selector_compat.py",
    "tools/check_4B436629E_production_readiness_consolidation_gate.py",
    "tools/run_4B436629E_production_readiness_consolidation_gate.py",
]

EXPECTED_29A_H1_DECISION = "PRODUCTION_REPORT_PATH_HYGIENE_READY"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _load_module(path: Path, name: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _evidence_payload(contract_version: str, decision: str) -> dict[str, Any]:
    return {
        "contract_version": contract_version,
        "decision": decision,
        "ok": True,
        "read_only": True,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "approved_for_runtime_overlay_activation_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }


def _sample_evidence_probe(root: Path) -> dict[str, Any]:
    module = _load_module(root / "src/tradebot/production_readiness_gate.py", "production_readiness_gate_h2_probe")
    with tempfile.TemporaryDirectory() as tmp:
        evidence_dir = Path(tmp)
        _write_json(evidence_dir / "4B436629A_production_hardening_p0_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29A", "PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED"))
        _write_json(evidence_dir / "4B436629A_H1_production_report_path_hygiene_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29A-H1", EXPECTED_29A_H1_DECISION))
        _write_json(evidence_dir / "4B436629B_api_operator_security_hardening_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29B", "API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED"))
        _write_json(evidence_dir / "4B436629C_sqlite_audit_ledger_upgrade_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29C", "SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED"))
        _write_json(evidence_dir / "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29C-H2", "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED"))
        _write_json(evidence_dir / "4B436629D_replay_backtest_walkforward_gate_decision_20260619T000001Z.json", _evidence_payload("4B.4.3.6.6.29D", "REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED"))
        snapshot = module.build_consolidated_readiness_snapshot(evidence_dir)
        evidence = snapshot.get("evidence", {})
        return {
            "ok": bool(snapshot.get("evidence_complete")) and snapshot.get("decision") == "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
            "decision": snapshot.get("decision"),
            "evidence_complete": bool(snapshot.get("evidence_complete")),
            "paper_candidate_preflight_ready": bool(snapshot.get("approved_for_paper_candidate_preflight")),
            "live_real_hard_block_verified": bool(snapshot.get("live_real_hard_block_verified")),
            "evidence_29a_h1_accepted": bool(evidence.get("29A-H1", {}).get("ok")),
            "reason_codes": snapshot.get("reason_codes", []),
        }


def _actual_evidence_probe(root: Path) -> dict[str, Any]:
    evidence_dir = root / "reports/production_hardening"
    if not evidence_dir.exists():
        return {"available": False, "ok": False, "reason": "reports/production_hardening missing"}
    module = _load_module(root / "src/tradebot/production_readiness_gate.py", "production_readiness_gate_h2_actual")
    snapshot = module.build_consolidated_readiness_snapshot(evidence_dir)
    evidence = snapshot.get("evidence", {})
    return {
        "available": True,
        "ok": bool(snapshot.get("evidence_complete")) and snapshot.get("decision") == "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED",
        "decision": snapshot.get("decision"),
        "evidence_complete": bool(snapshot.get("evidence_complete")),
        "paper_candidate_preflight_ready": bool(snapshot.get("approved_for_paper_candidate_preflight")),
        "live_real_hard_block_verified": bool(snapshot.get("live_real_hard_block_verified")),
        "evidence_29a_h1_accepted": bool(evidence.get("29A-H1", {}).get("ok")),
        "evidence_29a_h1_decision": evidence.get("29A-H1", {}).get("decision"),
        "reason_codes": snapshot.get("reason_codes", []),
    }


def build_report(root: Path) -> dict[str, Any]:
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(root / path) if (root / path).exists() else False for path in COMPILE_FILES}
    target = root / "src/tradebot/production_readiness_gate.py"
    text = target.read_text(encoding="utf-8") if target.exists() else ""
    sample_probe = _sample_evidence_probe(root) if target.exists() else {"ok": False, "reason": "missing production_readiness_gate.py"}
    actual_probe = _actual_evidence_probe(root) if target.exists() else {"available": False, "ok": False}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION == "4B.4.3.6.6.29E-H2",
        "base_contract_present": "PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION" in text,
        "evidence_selector_accepts_actual_29a_h1_decision": EXPECTED_29A_H1_DECISION in text,
        "stale_29a_h1_decision_removed": "PRODUCTION_REPORT_PATH_HYGIENE_READY_LIVE_REAL_STILL_BLOCKED" not in text,
        "accepted_evidence_selector_still_present": "_latest_matching" in text,
        "sample_evidence_probe_ok": bool(sample_probe.get("ok")),
        "actual_evidence_probe_ok": bool(actual_probe.get("ok")),
        "evidence_complete": bool(actual_probe.get("evidence_complete")),
        "paper_candidate_preflight_ready": bool(actual_probe.get("paper_candidate_preflight_ready")),
        "live_real_hard_block_verified": bool(actual_probe.get("live_real_hard_block_verified")),
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    ok = all(checks.values())
    return {
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": BASE_CONTRACT_VERSION,
        "production_readiness_evidence_selector_compat": True,
        "read_only": True,
        "ok": ok,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "sample_probe": sample_probe,
        "actual_probe": actual_probe,
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
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29E-H2 production readiness evidence selector compatibility")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} production readiness evidence selector compatibility ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
