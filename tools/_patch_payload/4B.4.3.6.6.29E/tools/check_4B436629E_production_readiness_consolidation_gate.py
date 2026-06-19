from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29E"
EXPECTED_FILES = [
    "docs/PRODUCTION_READINESS_CONSOLIDATION_GATE_4B436629E.md",
    "src/tradebot/production_readiness_gate.py",
    "tests/test_production_readiness_consolidation_gate_4B436629E.py",
    "tools/apply_4B436629E_production_readiness_consolidation_gate.py",
    "tools/check_4B436629E_production_readiness_consolidation_gate.py",
    "tools/rollback_4B436629E_production_readiness_consolidation_gate.py",
    "tools/run_4B436629E_production_readiness_consolidation_gate.py",
]
COMPILE_TARGETS = EXPECTED_FILES[1:]


def _compile(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in COMPILE_TARGETS:
        path = root / rel
        if not path.exists():
            out[rel] = False
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except py_compile.PyCompileError:
            out[rel] = False
    return out


def _load_module(root: Path) -> Any:
    module_path = root / "src/tradebot/production_readiness_gate.py"
    spec = importlib.util.spec_from_file_location("production_readiness_gate_probe", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load production_readiness_gate module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_report(root: Path) -> dict[str, Any]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = _compile(root)
    config_text = (root / "src/tradebot/config.py").read_text(encoding="utf-8") if (root / "src/tradebot/config.py").exists() else ""
    module_text = (root / "src/tradebot/production_readiness_gate.py").read_text(encoding="utf-8") if (root / "src/tradebot/production_readiness_gate.py").exists() else ""
    snapshot: dict[str, Any] = {}
    module_probe_ok = False
    try:
        module = _load_module(root)
        snapshot = module.build_consolidated_readiness_snapshot(root / "reports/production_hardening")
        module_probe_ok = bool(snapshot.get("ok"))
    except Exception as exc:
        snapshot = {"ok": False, "error": str(exc)}
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": f'PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION = "{CONTRACT_VERSION}"' in module_text,
        "config_consolidation_gate_fields_present": "production_readiness_consolidation_enabled" in config_text and "production_readiness_evidence_dir" in config_text,
        "evidence_merge_present": "load_production_hardening_evidence" in module_text,
        "paper_candidate_preflight_present": "approved_for_paper_candidate_preflight" in module_text,
        "live_real_hard_block_present": "live_real_hard_block_verified" in module_text,
        "module_probe_ok": module_probe_ok,
        "evidence_complete": bool(snapshot.get("evidence_complete", False)),
        "runtime_activation_blocked": "approved_for_runtime_overlay_activation_candidate=False" in module_text or '"approved_for_runtime_overlay_activation_candidate": False' in module_text,
        "paper_live_order_blocked": "paper_live_order_blocked=True" in module_text or '"paper_live_order_blocked": True' in module_text,
        "training_reload_blocked": "training_reload_blocked=True" in module_text or '"training_reload_blocked": True' in module_text,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "production_readiness_consolidation_gate": True,
        "read_only": True,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
        "snapshot": snapshot,
        "ok": all(checks.values()),
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
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29E production readiness consolidation gate")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
