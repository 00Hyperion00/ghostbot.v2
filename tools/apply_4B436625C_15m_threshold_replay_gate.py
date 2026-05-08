from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "tools/run_15m_threshold_replay_gate_4B436625C.py",
    "tests/test_mtf_threshold_replay_gate_4B436625C.py",
    "docs/MTF_THRESHOLD_REPLAY_GATE_RUNBOOK_4B436625C.md",
]
MARKERS = {
    "CONTRACT_VERSION": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "ThresholdReplayProfile": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "ThresholdReplayGateLimits": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "evaluate_threshold_replay_profile": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "replay_candidate_model_from_25b_report": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "MTF_THRESHOLD_REPLAY_EXPECTED_EDGE_LOW": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "MTF_THRESHOLD_REPLAY_ACTION_COVERAGE_LOW": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "approved_for_live_real": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "post_requests_allowed": "src/tradebot/mtf_threshold_replay_gate_25c.py",
    "--input-json": "tools/run_15m_threshold_replay_gate_4B436625C.py",
    "--candidate-model": "tools/run_15m_threshold_replay_gate_4B436625C.py",
    "--threshold-profiles": "tools/run_15m_threshold_replay_gate_4B436625C.py",
    "review-ok": "tools/run_15m_threshold_replay_gate_4B436625C.py",
    "test_threshold_replay_profile_can_pass_positive_edge_samples": "tests/test_mtf_threshold_replay_gate_4B436625C.py",
}

def main() -> int:
    print("4B.4.3.6.6.25C 15m threshold/calibration replay gate patch applied")
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
    for marker, rel in MARKERS.items():
        path = ROOT / rel
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        print(f" - {marker}_present: {present}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
