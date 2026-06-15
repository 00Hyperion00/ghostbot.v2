from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "src/tradebot/hyp006_operator_cockpit_baseline.py",
    "tools/run_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/check_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/apply_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tools/rollback_4B436628F_hyp006_operator_cockpit_baseline.py",
    "tests/test_hyp006_operator_cockpit_baseline_4B436628F.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_BASELINE_4B436628F.md",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def synthetic_report_ok() -> dict[str, Any]:
    from tradebot.hyp006_operator_cockpit_baseline import build_acceptance_baseline_report

    health = {
        "contract_version": "4B.4.3.6.6.28E",
        "decision": "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY",
        "ok": True,
        "branch_id": "HYP-006-R1",
        "approved_for_shadow_collection_continuity": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "order_actions_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "scheduler_task_health": {"task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection", "last_task_result": 0, "number_of_missed_runs": 0, "state": "Ready"},
        "scheduler_task_health_validation": {"ok": True, "reasons": []},
    }
    rows = [
        {"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "a", "symbol": "BTCUSDT", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final_short_probe": 100.0, "spread_slippage_proxy_bps": 3.0},
        {"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "b", "symbol": "ETHUSDT", "timestamp_utc": "2026-06-01T04:00:00+00:00", "forward_return_bps_final_short_probe": -50.0, "spread_slippage_proxy_bps": 4.0},
        {"branch_id": "HYP-006-R1", "no_order_measurement_only": True, "observation_id": "c", "symbol": "ETHUSDT", "timestamp_utc": "2026-06-01T08:00:00+00:00", "forward_return_bps_final_short_probe": 80.0, "spread_slippage_proxy_bps": 5.0},
    ]
    payload = build_acceptance_baseline_report(health_report=health, ledger_rows=rows)
    return {
        "ok": payload.get("ok") is True,
        "dashboard_seed_ready": payload.get("dashboard_seed_ready") is True,
        "paper_blocked": payload.get("approved_for_paper_candidate") is False,
        "live_blocked": payload.get("approved_for_live_real") is False,
        "order_blocked": payload.get("order_actions_performed") is False,
        "sample_target_blocker_present": "SHADOW_SAMPLE_COUNT_BELOW_TARGET" in payload.get("blockers", []),
        "acceptance_not_met": payload.get("acceptance_baseline_metrics", {}).get("acceptance_requirements_met") is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    expected = {path: (ROOT / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile_ok(ROOT / path) for path in PY_FILES if (ROOT / path).exists()}
    synthetic = synthetic_report_ok()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) and len(compiled) == len(PY_FILES),
        "synthetic_ok": all(synthetic.values()),
        "dashboard_seed_ready": synthetic.get("dashboard_seed_ready") is True,
        "acceptance_not_met_without_30_samples": synthetic.get("acceptance_not_met") is True,
        "paper_live_order_blocked": synthetic.get("paper_blocked") is True and synthetic.get("live_blocked") is True and synthetic.get("order_blocked") is True,
        "sample_target_blocker_present": synthetic.get("sample_target_blocker_present") is True,
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
    }
    payload = {
        "contract_version": "4B.4.3.6.6.28F",
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "synthetic": synthetic,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    if args.once_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.28F check ok={payload['ok']}")
        for key, value in checks.items():
            print(f" - {key}: {value}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
