from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    "src/tradebot/futures_companion_candidate_audit_runner.py",
    "tools/run_futures_companion_candidate_audit_runner_4B436625G.py",
    "tests/test_futures_companion_candidate_audit_runner_4B436625G.py",
]
MARKERS = {
    "src/tradebot/futures_companion_candidate_audit_runner.py": [
        "FUTURES_COMPANION_AUDIT_CONTRACT_VERSION",
        "FuturesCompanionCandidateSpec",
        "FuturesCompanionAuditLimits",
        "build_futures_companion_candidate_audit_runner",
        "COMPANION_AUDIT_READY",
        "COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED",
        "approved_for_live_real",
        "post_requests_allowed",
    ],
    "tools/run_futures_companion_candidate_audit_runner_4B436625G.py": [
        "__input_json",
        "__reports_dir",
        "__include_all",
        "__companion_symbols",
        "__review_ok",
        "spec_json",
    ],
    "tests/test_futures_companion_candidate_audit_runner_4B436625G.py": [
        "test_companion_audit_runner_generates_eth_spec_and_commands",
        "test_companion_audit_runner_blocks_when_companion_missing",
        "test_tool_writes_report_and_spec_from_input_json",
    ],
    "docs/FUTURES_COMPANION_CANDIDATE_AUDIT_RUNNER_RUNBOOK_4B436625G.md": [
        "Futures Companion Candidate Audit Runner",
        "Training remains blocked",
        "Paper/live remain blocked",
    ],
}


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"COMPILE_ERROR {path}: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25G futures companion candidate audit runner patch applied")
    ok = True
    for rel in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = _compile(path)
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
    for rel, markers in MARKERS.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for marker in markers:
            present = marker.replace("-", "_") in text.replace("-", "_")
            print(f" - {marker.replace('-', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
