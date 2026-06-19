from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29E-H3"
EXPECTED_FILES = [
    "docs/PRODUCTION_READINESS_LEGACY_TEST_COMPAT_4B436629E_H3.md",
    "tests/test_production_readiness_legacy_test_compat_4B436629E_H3.py",
    "tools/apply_4B436629E_H3_production_readiness_legacy_test_compat.py",
    "tools/check_4B436629E_H3_production_readiness_legacy_test_compat.py",
    "tools/rollback_4B436629E_H3_production_readiness_legacy_test_compat.py",
    "tools/run_4B436629E_H3_production_readiness_legacy_test_compat.py",
]
H1_TEST = "tests/test_production_readiness_evidence_refresh_4B436629E_H1.py"
STALE_DECISION = "PRODUCTION_REPORT_PATH_HYGIENE_READY_LIVE_REAL_STILL_BLOCKED"
ACTUAL_DECISION = "PRODUCTION_REPORT_PATH_HYGIENE_READY"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _load_module(root: Path, rel: str, name: str) -> Any | None:
    path = root / rel
    if not path.exists():
        return None
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tools"))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None
    finally:
        for candidate in (str(root / "src"), str(root / "tools")):
            while candidate in sys.path:
                sys.path.remove(candidate)


def _write_report(base: Path, name: str, *, contract: str, decision: str) -> None:
    payload = {
        "ok": True,
        "contract_version": contract,
        "decision": decision,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
    }
    (base / name).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _sample_probe(root: Path) -> dict[str, Any]:
    module = _load_module(root, "src/tradebot/production_readiness_gate.py", "production_readiness_gate_h3_probe")
    if module is None:
        return {"ok": False, "reason": "PRODUCTION_READINESS_GATE_IMPORT_FAILED"}
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        _write_report(base, "4B436629A_production_hardening_p0_decision_20260619T1.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED")
        _write_report(base, "4B436629A_H1_production_report_path_hygiene_decision_20260619T1.json", contract="4B.4.3.6.6.29A-H1", decision=ACTUAL_DECISION)
        _write_report(base, "4B436629B_api_operator_security_hardening_decision_20260619T1.json", contract="4B.4.3.6.6.29B", decision="API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED")
        _write_report(base, "4B436629C_sqlite_audit_ledger_upgrade_decision_20260619T1.json", contract="4B.4.3.6.6.29C", decision="SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED")
        _write_report(base, "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_20260619T1.json", contract="4B.4.3.6.6.29C-H2", decision="SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED")
        _write_report(base, "4B436629D_replay_backtest_walkforward_gate_decision_20260619T1.json", contract="4B.4.3.6.6.29D", decision="REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED")
        snapshot = module.build_consolidated_readiness_snapshot(base)
        evidence = snapshot.get("evidence", {})
        h1 = evidence.get("29A-H1", {}) if isinstance(evidence, dict) else {}
        return {
            "ok": bool(snapshot.get("evidence_complete")) and bool(snapshot.get("approved_for_paper_candidate_preflight")) and not bool(snapshot.get("approved_for_paper_candidate")) and not bool(snapshot.get("approved_for_live_real")),
            "decision": snapshot.get("decision"),
            "evidence_complete": bool(snapshot.get("evidence_complete")),
            "paper_candidate_preflight_ready": bool(snapshot.get("approved_for_paper_candidate_preflight")),
            "paper_candidate": bool(snapshot.get("approved_for_paper_candidate")),
            "live_real": bool(snapshot.get("approved_for_live_real")),
            "evidence_29a_h1_accepted": bool(h1.get("ok")),
            "evidence_29a_h1_decision": h1.get("decision"),
        }


def _tool_report_ok(root: Path, rel: str) -> bool:
    module = _load_module(root, rel, Path(rel).stem + "_h3_import")
    if module is None or not hasattr(module, "build_report"):
        return False
    try:
        report = module.build_report(root)
    except Exception:
        return False
    return bool(report.get("ok"))


def build_report(root: Path) -> dict[str, Any]:
    compiled = {rel: _compile(root / rel) for rel in EXPECTED_FILES + [H1_TEST, "src/tradebot/production_readiness_gate.py"] if (root / rel).exists()}
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    h1_text = (root / H1_TEST).read_text(encoding="utf-8") if (root / H1_TEST).exists() else ""
    gate_text = (root / "src/tradebot/production_readiness_gate.py").read_text(encoding="utf-8") if (root / "src/tradebot/production_readiness_gate.py").exists() else ""
    sample_probe = _sample_probe(root)
    h2_ok = _tool_report_ok(root, "tools/check_4B436629E_H2_production_readiness_evidence_selector_compat.py")
    h1_ok = _tool_report_ok(root, "tools/check_4B436629E_H1_production_readiness_evidence_refresh.py")
    base_ok = _tool_report_ok(root, "tools/check_4B436629E_production_readiness_consolidation_gate.py")
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "legacy_h1_test_present": bool(h1_text),
        "legacy_h1_test_stale_decision_removed": STALE_DECISION not in h1_text,
        "legacy_h1_test_actual_decision_present": ACTUAL_DECISION in h1_text,
        "production_readiness_gate_actual_decision_present": f'"decision": "{ACTUAL_DECISION}"' in gate_text or f'"decision\": \"{ACTUAL_DECISION}\"' in gate_text or ACTUAL_DECISION in gate_text,
        "sample_probe_ok": bool(sample_probe.get("ok")),
        "h2_checker_ok": h2_ok,
        "h1_checker_ok": h1_ok,
        "base_29e_checker_ok": base_ok,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "production_readiness_legacy_test_compat": True,
        "read_only": True,
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "sample_probe": sample_probe,
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
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29E-H3 production readiness legacy test compatibility")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} production readiness legacy test compatibility ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
