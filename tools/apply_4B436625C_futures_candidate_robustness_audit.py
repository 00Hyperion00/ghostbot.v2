from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/futures_candidate_robustness_audit.py",
    "tools/run_futures_candidate_robustness_audit_4B436625C.py",
    "tests/test_futures_candidate_robustness_audit_4B436625C.py",
    "docs/FUTURES_CANDIDATE_ROBUSTNESS_AUDIT_RUNBOOK_4B436625C.md",
]
MARKERS = {
    "src/tradebot/futures_candidate_robustness_audit.py": [
        "FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION",
        "FuturesRobustnessLimits",
        "build_futures_candidate_robustness_audit",
        "ROBUSTNESS_CANDIDATE_CONFIRMED",
        "NO_FUTURES_ROBUSTNESS_CANDIDATE_PASSED",
        "approved_for_live_real",
        "post_requests_allowed",
        "FUNDING_COVERAGE_DETAIL_UNAVAILABLE",
        "OUTLIER_DEPENDENCY_DETAIL_UNAVAILABLE",
    ],
    "tools/run_futures_candidate_robustness_audit_4B436625C.py": [
        "--input-json",
        "--reports-dir",
        "--include-all",
        "--review-ok",
        "observation-only",
    ],
    "tests/test_futures_candidate_robustness_audit_4B436625C.py": [
        "test_robustness_audit_passes_confirmed_futures_candidate",
        "test_robustness_audit_blocks_negative_candidate",
        "test_tool_writes_report_from_input_json",
    ],
    "docs/FUTURES_CANDIDATE_ROBUSTNESS_AUDIT_RUNBOOK_4B436625C.md": [
        "Futures Candidate Robustness",
        "Backtest PASS is not paper permission",
        "Paper PASS is not live permission",
    ],
}


def main() -> int:
    print("4B.4.3.6.6.25C futures candidate robustness / data coverage audit patch applied")
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        if exists and path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
                ok = True
            except py_compile.PyCompileError:
                ok = False
            print(f" - {rel}_py_compile_ok: {ok}")
    for rel, markers in MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for marker in markers:
            print(f" - {marker.replace('-', '_')}_present: {marker in text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
