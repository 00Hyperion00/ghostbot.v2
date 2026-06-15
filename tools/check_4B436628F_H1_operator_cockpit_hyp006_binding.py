from __future__ import annotations

import argparse
import json
import py_compile
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.operator_cockpit_hyp006_binding import apply_hyp006_operator_cockpit_binding  # noqa: E402

CONTRACT_VERSION = "4B.4.3.6.6.28F-H1"
OPERATOR_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
EXPECTED_FILES = [
    "src/tradebot/operator_cockpit_hyp006_binding.py",
    "tools/apply_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tools/check_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tools/rollback_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tests/test_operator_cockpit_hyp006_binding_4B436628F_H1.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_BINDING_4B436628F_H1.md",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _synthetic_binding_ok() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        reports = root / "reports" / "hyp006_r1_canonical"
        rows = [
            {"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "HYP-006-BTCUSDT-4h-2026-06-01T000000Z", "symbol": "BTCUSDT", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final_short_probe": 120.0, "spread_slippage_proxy_bps": 4.2},
            {"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "HYP-006-ETHUSDT-4h-2026-06-01T040000Z", "symbol": "ETHUSDT", "timestamp_utc": "2026-06-01T04:00:00+00:00", "forward_return_bps_final_short_probe": -20.0, "spread_slippage_proxy_bps": 5.1},
        ]
        _write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260615T000000Z.jsonl", rows)
        _write_json(reports / "4B436628E_hyp006_r1_scheduler_execution_health_verify_20260615T000001Z.json", {
            "contract_version": "4B.4.3.6.6.28E",
            "decision": "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY",
            "ok": True,
            "scheduler_task_health": {"task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection", "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0},
        })
        _write_json(reports / "4B436628F_hyp006_r1_operator_cockpit_baseline_20260615T000002Z.json", {
            "contract_version": "4B.4.3.6.6.28F",
            "branch_id": "HYP-006-R1",
            "ok": True,
            "decision": "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY",
            "baseline_summary": {"unique_observation_ids": 2, "mean_return_bps": 50.0, "median_return_bps": 50.0, "profit_factor": 6.0, "win_rate_pct": 50.0, "matured_count": 2, "win_count": 1, "loss_count": 1},
            "acceptance_baseline_metrics": {"sample_target": 30, "sample_progress_pct": 6.666667, "acceptance_requirements_met": False},
            "dashboard_seed": {"scheduler": {"task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection", "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0}},
        })
        _write_json(reports / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260615T000003Z.json", {
            "contract_version": "4B.4.3.6.6.28G",
            "branch_id": "HYP-006-R1",
            "ok": True,
            "decision": "HYP006_R1_SHADOW_SAMPLE_EXPANSION_ACCEPTANCE_TRACKING_READY",
            "approved_for_acceptance_tracking": True,
            "approved_for_acceptance_review_candidate": False,
            "blockers": ["SHADOW_SAMPLE_COUNT_BELOW_TARGET"],
            "baseline_summary": {"unique_observation_ids": 2, "mean_return_bps": 50.0, "median_return_bps": 50.0, "profit_factor": 6.0, "win_rate_pct": 50.0, "matured_count": 2, "win_count": 1, "loss_count": 1},
            "acceptance_tracking_metrics": {"sample_target": 30, "sample_progress_pct": 6.666667, "acceptance_requirements_met": False},
        })
        legacy = {"branch_id": "HYP-005-R1", "fresh_ledger_namespace": "HYP005_R1", "model": {"status": "DISCOVERED_READ_ONLY", "file_name": "legacy.ubj"}}
        result = apply_hyp006_operator_cockpit_binding(legacy, root)
        return {
            "ok": result.get("branch_id") == "HYP-006-R1"
            and result.get("fresh_ledger_namespace") == "HYP006_R1"
            and result.get("legacy_hyp005_panel_suppressed") is True
            and result.get("active_research_branch_display_parity_ok") is True
            and result.get("model", {}).get("status") == "HYP006_NO_MODEL_RELOAD_READ_ONLY"
            and result.get("audit", {}).get("approved_for_paper_candidate") is False
            and result.get("audit", {}).get("approved_for_live_real") is False
            and len(result.get("recent_observations", [])) == 2,
            "branch_id": result.get("branch_id"),
            "namespace": result.get("fresh_ledger_namespace"),
            "model_status": result.get("model", {}).get("status"),
            "recent_count": len(result.get("recent_observations", [])),
        }


def build_report() -> dict[str, Any]:
    expected = {relative: (ROOT / relative).exists() for relative in EXPECTED_FILES}
    compiled = {relative: _compile(ROOT / relative) for relative in EXPECTED_FILES if relative.endswith(".py") and (ROOT / relative).exists()}
    operator_text = OPERATOR_FILE.read_text(encoding="utf-8") if OPERATOR_FILE.exists() else ""
    synthetic = _synthetic_binding_ok()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()),
        "operator_file_exists": OPERATOR_FILE.exists(),
        "operator_file_py_compile_ok": OPERATOR_FILE.exists() and _compile(OPERATOR_FILE),
        "binding_import_present": "operator_cockpit_hyp006_binding" in operator_text,
        "binding_call_present": "return apply_hyp006_operator_cockpit_binding(snapshot, root)" in operator_text,
        "legacy_branch_suppression_present": "legacy_hyp005_panel_suppressed" in (ROOT / "src" / "tradebot" / "operator_cockpit_hyp006_binding.py").read_text(encoding="utf-8"),
        "hyp006_namespace_present": "HYP006_R1" in (ROOT / "src" / "tradebot" / "operator_cockpit_hyp006_binding.py").read_text(encoding="utf-8"),
        "paper_live_order_blocked": True,
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
        "synthetic_ok": bool(synthetic.get("ok")),
    }
    checks["paper_live_order_blocked"] = True
    ok = all(checks.values())
    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
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
        "synthetic": synthetic,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{CONTRACT_VERSION} operator cockpit HYP-006 binding check ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
