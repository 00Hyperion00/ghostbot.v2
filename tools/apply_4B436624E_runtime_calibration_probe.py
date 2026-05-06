from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/runtime_calibration_probe.py",
    "tools/run_runtime_calibration_probe_4B436624E.py",
    "tests/test_runtime_calibration_probe_4B436624E.py",
    "docs/RUNTIME_CALIBRATION_PROBE_RUNBOOK_4B436624E.md",
]

TOKENS = {
    "src/tradebot/runtime_calibration_probe.py": [
        "RUNTIME_CALIBRATION_PROBE_CONTRACT_VERSION",
        "calibrate_probabilities",
        "build_runtime_calibration_probe",
        "CALIBRATION_SUPPRESSION",
        "RAW_MODEL_COLLAPSE",
    ],
    "tools/run_runtime_calibration_probe_4B436624E.py": [
        "method=\"GET\"",
        "post_requests_allowed",
        "REPORT_PREFIX",
        "SWEEP_PREFIX",
        "--input-json",
    ],
}


def main() -> None:
    print("4B.4.3.6.6.24E runtime calibration probe / threshold sweep patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if exists and path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)
            print(f" - {rel}_py_compile_ok: True")
    for rel, needles in TOKENS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for needle in needles:
            print(f" - {needle}_present: {needle in text}")


if __name__ == "__main__":
    main()
