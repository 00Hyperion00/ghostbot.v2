from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/two_stage_action_side_recovery.py",
    "tools/run_two_stage_action_side_recovery_4B436624K.py",
    "tests/test_two_stage_action_side_recovery_4B436624K.py",
    "docs/TWO_STAGE_ACTION_SIDE_RECOVERY_RUNBOOK_4B436624K.md",
]
MARKERS = {
    "src/tradebot/two_stage_action_side_recovery.py": [
        "TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION",
        "TwoStageActionSideCandidateSpec",
        "TwoStageGateLimits",
        "train_two_stage_candidate",
        "evaluate_two_stage_training_result",
        "ACTION_HOLD_PROBABILITY_GAP_LOW",
        "SIDE_ACCURACY_LOW",
        "approved_for_live_real",
    ],
    "tools/run_two_stage_action_side_recovery_4B436624K.py": [
        "--input-json",
        "--candidate-json",
        "--promote",
        "promotion_requires_explicit_flag",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_two_stage_action_side_recovery_4B436624K.py": [
        "test_two_stage_candidate_gate_can_pass_mock_result",
        "test_tool_writes_report_from_candidate_json",
    ],
}


def main() -> int:
    print("4B.4.3.6.6.24K two-stage action/side model recovery patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        print(f" - {rel}_exists: {path.exists()}")
        if path.suffix == ".py" and path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
                print(f" - {rel}_py_compile_ok: True")
            except Exception as exc:  # pragma: no cover
                print(f" - {rel}_py_compile_ok: False ({exc})")
                return 1
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            print(f" - {marker}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
