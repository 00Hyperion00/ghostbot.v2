from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/cost_aware_retrain_sweep.py",
    "tools/run_cost_aware_retrain_sweep_4B436624J.py",
    "tests/test_cost_aware_retrain_sweep_4B436624J.py",
    "docs/COST_AWARE_RETRAIN_SWEEP_RUNBOOK_4B436624J.md",
]
MARKERS = {
    "src/tradebot/cost_aware_retrain_sweep.py": [
        "COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION",
        "CostAwareRetrainCandidateSpec",
        "CostAwareRetrainGateLimits",
        "train_cost_aware_candidate",
        "evaluate_cost_aware_training_result",
        "BUY_SELL_SEPARATION_MEAN_LOW",
        "LOW_MARGIN_REJECTION_HIGH",
        "approved_for_live_real",
    ],
    "tools/run_cost_aware_retrain_sweep_4B436624J.py": [
        "REPORT_PREFIX",
        "--input-json",
        "--promote",
        "promotion_requires_explicit_flag",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_cost_aware_retrain_sweep_4B436624J.py": [
        "test_cost_aware_retrain_candidate_gate_can_pass_mock_result",
        "test_tool_writes_report_from_candidate_json",
    ],
}


def main() -> int:
    print("4B.4.3.6.6.24J cost-aware retrain sweep + separation gate patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if exists and path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                print(f" - {rel}_py_compile_ok: True")
            except Exception as exc:
                print(f" - {rel}_py_compile_ok: False ({exc})")
                return 1
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            print(f" - {marker}_present: {marker in text}")
            if marker not in text:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
