from __future__ import annotations

import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.24H"
ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    Path("src/tradebot/label_horizon_recovery.py"),
    Path("tools/run_label_horizon_recovery_4B436624H.py"),
    Path("tests/test_label_horizon_recovery_4B436624H.py"),
    Path("docs/LABEL_HORIZON_RECOVERY_RUNBOOK_4B436624H.md"),
]

MARKERS = {
    "src/tradebot/label_horizon_recovery.py": [
        "LABEL_HORIZON_RECOVERY_CONTRACT_VERSION",
        "LabelPolicyCandidate",
        "build_label_horizon_recovery",
        "TARGET_ACTION_COVERAGE_HIGH",
        "FORWARD_RETURN_SEPARATION_LOW",
        "approved_for_live_real",
    ],
    "tools/run_label_horizon_recovery_4B436624H.py": [
        "REPORT_PREFIX",
        "--input-csv",
        "--input-json",
        "method=\"GET\"",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_label_horizon_recovery_4B436624H.py": [
        "test_label_horizon_gate_passes_balanced_directional_policy",
        "test_tool_writes_report_from_input_csv",
    ],
}


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8")
    except Exception:
        return False


def main() -> None:
    print(f"{PHASE} label horizon / target engineering recovery patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        print(f" - {rel.as_posix()}_exists: {path.exists()}")
        if path.suffix == ".py":
            print(f" - {rel.as_posix()}_py_compile_ok: {compile_ok(path)}")
    for rel, markers in MARKERS.items():
        path = ROOT / rel
        for marker in markers:
            print(f" - {marker}_present: {contains(path, marker)}")


if __name__ == "__main__":
    main()
