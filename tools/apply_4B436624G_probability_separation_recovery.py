from __future__ import annotations

import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.24G"
ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    Path("src/tradebot/probability_separation_gate.py"),
    Path("tools/run_probability_separation_recovery_4B436624G.py"),
    Path("tests/test_probability_separation_gate_4B436624G.py"),
    Path("docs/PROBABILITY_SEPARATION_RECOVERY_RUNBOOK_4B436624G.md"),
]

MARKERS = {
    "src/tradebot/probability_separation_gate.py": [
        "PROBABILITY_SEPARATION_GATE_CONTRACT_VERSION",
        "build_probability_separation_gate",
        "build_label_calibration_report",
        "BUY_SELL_SEPARATION_MEAN_LOW",
        "LOW_MARGIN_REJECTION_HIGH",
        "approved_for_live_real",
    ],
    "tools/run_probability_separation_recovery_4B436624G.py": [
        "REPORT_PREFIX",
        "--input-json",
        "--training-json",
        "method=\"GET\"",
        "post_requests_allowed",
        "review-ok",
    ],
    "tests/test_probability_separation_gate_4B436624G.py": [
        "test_separation_gate_blocks_tight_buy_sell_probability_gap",
        "test_tool_writes_report_from_input_json",
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
    print(f"{PHASE} probability separation / label calibration recovery patch applied")
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
