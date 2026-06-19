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

EXPECTED_FILES = [
    "src/tradebot/hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tests/test_hyp006_fresh_shadow_cycle_oos_delta_review_4B436628G_H9.py",
    "tools/apply_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/check_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/run_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "tools/rollback_4B436628G_H9_hyp006_fresh_shadow_cycle_oos_delta_review.py",
    "docs/HYP006_R1_FRESH_SHADOW_CYCLE_OOS_DELTA_REVIEW_4B436628G_H9.md",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _sample_probe() -> dict[str, Any]:
    from tradebot.hyp006_fresh_shadow_cycle_oos_delta_review import READY_DECISION, build_fresh_shadow_cycle_oos_delta_review

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        _write(base / "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_20260618T210504Z.json", {
            "contract_version": "4B.4.3.6.6.28G-H3", "read_only": True, "candidate_count": 20, "near_miss_count": 10, "trigger_count": 0, "scanned_candle_count": 100, "symbol_near_miss_counter": {"BNBUSDT": 5}, "symbol_candidate_counter": {"BNBUSDT": 6}
        })
        _write(base / "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_20260619T210504Z.json", {
            "contract_version": "4B.4.3.6.6.28G-H3", "read_only": True, "candidate_count": 22, "near_miss_count": 12, "trigger_count": 0, "scanned_candle_count": 100, "symbol_near_miss_counter": {"BNBUSDT": 6}, "symbol_candidate_counter": {"BNBUSDT": 7}
        })
        for name, contract, decision in [
            ("4B436628G_H4_hyp006_r1_near_miss_outcome_attribution_20260619T220001Z.json", "4B.4.3.6.6.28G-H4", "HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY"),
            ("4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_20260619T220002Z.json", "4B.4.3.6.6.28G-H5", "HYP006_R1_COUNTERFACTUAL_FILTER_CANDIDATE_RANKING_READY"),
            ("4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_20260619T220003Z.json", "4B.4.3.6.6.28G-H6", "HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_READY"),
            ("4B436628G_H7_hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_20260619T220004Z.json", "4B.4.3.6.6.28G-H7", "NO_ORDER_BNBUSDT_PRIMARY_OVERLAY_SHADOW_MEASUREMENT_READY"),
        ]:
            _write(base / name, {"contract_version": contract, "decision": decision, "read_only": True})
        _write(base / "4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_20260619T220005Z.json", {
            "contract_version": "4B.4.3.6.6.28G-H8",
            "decision": "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED",
            "ok": True,
            "approved_for_bnbusdt_oos_evaluation": True,
            "approved_for_oos_monitoring_continuation": True,
            "approved_for_runtime_overlay_activation_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "training_performed": False,
            "reload_performed": False,
            "trading_action_performed": False,
            "order_actions_performed": False,
            "oos_guard_pass": True,
            "oos_guard_reasons": [],
            "latest_bnbusdt_measurement_summary": {"symbol": "BNBUSDT", "event_count": 14, "matured_count": 14, "win_rate_pct": 76.9, "mean_return_bps": 126.6, "profit_factor": 5.4, "worst_return_bps": -312.0, "worst_mae_bps": -426.0, "net_return_bps": 1645.0},
            "oos_delta_summary": {"event_count_delta": 1, "matured_count_delta": 1, "mean_return_bps_delta": 25.0, "profit_factor_delta": 1.1, "worst_return_bps_delta": 0.0, "worst_mae_bps_delta": 0.0},
            "tail_risk_assessment": {"tail_risk_monitoring_required": True, "tail_risk_reasons": ["WORST_MAE_MONITORING_REQUIRED"]},
        })
        report = build_fresh_shadow_cycle_oos_delta_review(base)
        return {
            "ok": report.get("decision") == READY_DECISION,
            "decision": report.get("decision"),
            "matured_count": report.get("bnbusdt_matured_count"),
            "matured_count_delta": report.get("bnbusdt_matured_count_delta"),
            "paper_transition_blocked": report.get("approved_for_paper_transition_candidate") is False,
            "live_real_blocked": report.get("approved_for_live_real") is False,
        }


def build_report() -> dict[str, Any]:
    expected_files = {path: (ROOT / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(ROOT / path) if (ROOT / path).exists() and path.endswith(".py") else True for path in EXPECTED_FILES}
    try:
        from tradebot.hyp006_fresh_shadow_cycle_oos_delta_review import CONTRACT_VERSION, RISK_FLAGS
        probe = _sample_probe()
        module_import_ok = True
        contract_version = CONTRACT_VERSION
        risk_flags = RISK_FLAGS
    except Exception as exc:
        probe = {"ok": False, "reason": f"MODULE_PROBE_FAILED:{exc}"}
        module_import_ok = False
        contract_version = None
        risk_flags = {}
    checks = {
        "all_expected_files_present": all(expected_files.values()),
        "all_py_compile_ok": all(compiled.values()),
        "contract_version_ok": contract_version == "4B.4.3.6.6.28G-H9",
        "fresh_h3_delta_review_present": module_import_ok,
        "sample_probe_ok": bool(probe.get("ok")),
        "paper_transition_blocked": bool(probe.get("paper_transition_blocked")),
        "live_real_blocked": bool(probe.get("live_real_blocked")),
        "runtime_activation_blocked": risk_flags.get("runtime_activation_blocked") is True,
        "paper_live_order_blocked": risk_flags.get("paper_live_order_blocked") is True,
        "training_reload_blocked": risk_flags.get("training_reload_blocked") is True,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": "4B.4.3.6.6.28G-H9",
        "checks": checks,
        "expected_files": expected_files,
        "compiled": compiled,
        "module_probe": probe,
        "read_only": True,
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
    report = build_report()
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print("4B.4.3.6.6.28G-H9 HYP-006 fresh shadow cycle OOS delta review checker")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
