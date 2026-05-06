from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/multitimeframe_retrain_sweep_25b.py",
    "tools/run_multitimeframe_retrain_sweep_4B436625B.py",
    "tests/test_multitimeframe_retrain_sweep_4B436625B.py",
]
MARKERS = {
    "src/tradebot/multitimeframe_retrain_sweep_25b.py": [
        "CONTRACT_VERSION",
        "MultiTimeframeRetrainCandidateSpec",
        "MultiTimeframeRetrainGateLimits",
        "train_mtf_15m_candidate",
        "evaluate_mtf_retrain_candidate_result",
        "MTF_RETRAIN_EXPECTED_EDGE_PROXY_LOW",
        "MTF_RETRAIN_ACTION_HOLD_SEPARATION_MEAN_LOW",
        "approved_for_live_real",
        "post_requests_allowed",
    ],
    "tools/run_multitimeframe_retrain_sweep_4B436625B.py": [
        "--input-json",
        "--candidate-json",
        "--promote",
        "promotion_performed",
        "review-ok",
    ],
    "tests/test_multitimeframe_retrain_sweep_4B436625B.py": [
        "test_mtf_retrain_candidate_gate_can_pass_mock_result",
        "test_tool_writes_report_from_candidate_json",
    ],
}

def main() -> int:
    print("4B.4.3.6.6.25B 15m multi-timeframe retrain sweep + gate patch applied")
    ok = True
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                compiled = True
            except Exception as exc:
                compiled = False
                print(f"   compile_error: {exc}")
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            present = marker in text
            print(f" - {marker}_present: {present}")
            ok = ok and present
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
