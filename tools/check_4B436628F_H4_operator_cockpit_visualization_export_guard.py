from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "4B.4.3.6.6.28F-H4"
EXPECTED = [
    "src/tradebot/operator_cockpit_hyp006_visualization_export_guard_hotfix.py",
    "tools/apply_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tools/check_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tools/rollback_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tests/test_operator_cockpit_visualization_export_guard_4B436628F_H4.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_VISUALIZATION_EXPORT_GUARD_4B436628F_H4.md",
]
COMPILE = EXPECTED[:-1] + [
    "src/tradebot/operator_cockpit_hyp006_binding.py",
    "src/tradebot/operator_cockpit_v2_read_only.py",
]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    once_json = "--once-json" in sys.argv
    expected = {rel: (ROOT / rel).exists() for rel in EXPECTED}
    compiled = {rel: _compile_ok(ROOT / rel) for rel in COMPILE if (ROOT / rel).exists() and rel.endswith(".py")}
    ro = (ROOT / "src/tradebot/operator_cockpit_v2_read_only.py").read_text(encoding="utf-8")
    binding = (ROOT / "src/tradebot/operator_cockpit_hyp006_binding.py").read_text(encoding="utf-8")
    helper = (ROOT / "src/tradebot/operator_cockpit_hyp006_visualization_export_guard_hotfix.py").read_text(encoding="utf-8")
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": VERSION in ro and VERSION in binding and VERSION in helper,
        "cumulative_progress_visual_present": "cumulative_samples" in ro and "cumulative_samples" in binding,
        "mae_mfe_proxy_present": "build_hyp006_mae_mfe_proxy_scatter" in binding,
        "risk_sizing_guard_present": "Risk-Sizing Evidence Yok" in ro and "RISK_SIZING_RUNTIME_EVENT_NOT_FOUND" in helper,
        "legacy_hyp005_source_cleanup_present": "sanitize_hyp006_audit_sources" in binding,
        "paper_live_order_blocked": "paper_live_order_enablement_present" in (ROOT / "tools/apply_4B436628F_H4_operator_cockpit_visualization_export_guard.py").read_text(encoding="utf-8"),
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
    }
    payload = {
        "ok": all(checks.values()),
        "contract_version": VERSION,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
    }
    if once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
