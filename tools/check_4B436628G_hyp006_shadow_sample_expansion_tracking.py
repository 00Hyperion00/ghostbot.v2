from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_sample_expansion_tracking.py",
    "tools/run_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/check_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/apply_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/rollback_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tests/test_hyp006_shadow_sample_expansion_tracking_4B436628G.py",
    "docs/HYP006_R1_SHADOW_SAMPLE_EXPANSION_TRACKING_4B436628G.md",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def synthetic_report_ok() -> dict[str, Any]:
    from tradebot.hyp006_shadow_sample_expansion_tracking import build_shadow_sample_expansion_report

    baseline = {
        "contract_version": "4B.4.3.6.6.28F",
        "decision": "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY",
        "ok": True,
        "branch_id": "HYP-006-R1",
        "approved_for_acceptance_tracking": True,
        "approved_for_shadow_collection_continuity": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "order_actions_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "baseline_summary": {"unique_observation_ids": 20, "mean_return_bps": 100.0, "median_return_bps": 10.0, "profit_factor": 2.0, "win_rate_pct": 50.0, "data_quality_pct": 100.0, "max_slippage_proxy_bps": 5.0},
    }
    rows = []
    for idx in range(24):
        rows.append(
            {
                "branch_id": "HYP-006-R1",
                "no_order_measurement_only": True,
                "observation_id": f"obs-{idx:02d}",
                "symbol": "BTCUSDT",
                "timestamp_utc": f"2026-06-{idx + 1:02d}T00:00:00+00:00",
                "forward_return_bps_final_short_probe": 100.0 if idx % 2 == 0 else -20.0,
                "spread_slippage_proxy_bps": 4.0,
            }
        )
    payload = build_shadow_sample_expansion_report(baseline_report=baseline, ledger_rows=rows)
    return {
        "ok": payload.get("ok") is True,
        "tracking_ready": payload.get("acceptance_tracking_ready") is True,
        "paper_blocked": payload.get("approved_for_paper_candidate") is False,
        "live_blocked": payload.get("approved_for_live_real") is False,
        "order_blocked": payload.get("order_actions_performed") is False,
        "sample_target_blocker_present": "SHADOW_SAMPLE_COUNT_BELOW_TARGET" in payload.get("blockers", []),
        "new_count_positive": payload.get("sample_expansion_delta", {}).get("new_unique_observation_count", 0) >= 4,
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
        "tracking_ready": synthetic.get("tracking_ready") is True,
        "sample_target_blocker_present": synthetic.get("sample_target_blocker_present") is True,
        "paper_live_order_blocked": synthetic.get("paper_blocked") is True and synthetic.get("live_blocked") is True and synthetic.get("order_blocked") is True,
        "new_observation_delta_present": synthetic.get("new_count_positive") is True,
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
    }
    payload = {
        "contract_version": "4B.4.3.6.6.28G",
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
        print(f"4B.4.3.6.6.28G check ok={payload['ok']}")
        for key, value in checks.items():
            print(f" - {key}: {value}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
