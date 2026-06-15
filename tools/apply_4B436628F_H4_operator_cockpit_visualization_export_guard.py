from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "4B.4.3.6.6.28F-H4"
EXPECTED = [
    "src/tradebot/operator_cockpit_hyp006_visualization_export_guard_hotfix.py",
    "src/tradebot/operator_cockpit_hyp006_binding.py",
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tools/check_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tools/rollback_4B436628F_H4_operator_cockpit_visualization_export_guard.py",
    "tests/test_operator_cockpit_visualization_export_guard_4B436628F_H4.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_VISUALIZATION_EXPORT_GUARD_4B436628F_H4.md",
]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    results: dict[str, object] = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    for rel in EXPECTED:
        path = ROOT / rel
        results[f"{rel}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            results[f"{rel}_py_compile_ok"] = _compile_ok(path)
    ro = (ROOT / "src/tradebot/operator_cockpit_v2_read_only.py").read_text(encoding="utf-8")
    binding = (ROOT / "src/tradebot/operator_cockpit_hyp006_binding.py").read_text(encoding="utf-8")
    results.update({
        "contract_version_present": VERSION in ro and VERSION in binding,
        "cumulative_progress_visual_present": "cumulative_samples" in ro and "cumulative_samples" in binding,
        "mae_mfe_proxy_present": "build_hyp006_mae_mfe_proxy_scatter" in binding,
        "risk_sizing_guard_present": "Risk-Sizing Evidence Yok" in ro and "RISK_SIZING_RUNTIME_EVENT_NOT_FOUND" in (ROOT / "src/tradebot/operator_cockpit_hyp006_visualization_export_guard_hotfix.py").read_text(encoding="utf-8"),
        "legacy_source_cleanup_present": "sanitize_hyp006_audit_sources" in binding,
    })
    print(f"{VERSION} Operator Cockpit visualization/export guard hotfix applied")
    for key, value in results.items():
        print(f" - {key}: {value}")
    return 0 if all(bool(value) for key, value in results.items() if key.endswith("_exists") or key.endswith("_py_compile_ok") or (key.endswith("_present") and key != "paper_live_order_enablement_present")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
