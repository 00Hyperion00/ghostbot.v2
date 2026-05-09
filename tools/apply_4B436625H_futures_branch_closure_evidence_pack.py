from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "src/tradebot/futures_branch_closure_evidence_pack.py",
    "tools/run_futures_branch_closure_evidence_pack_4B436625H.py",
    "tests/test_futures_branch_closure_evidence_pack_4B436625H.py",
]
MARKERS = {
    "src/tradebot/futures_branch_closure_evidence_pack.py": [
        "FUTURES_BRANCH_CLOSURE_CONTRACT_VERSION",
        "FuturesBranchClosureLimits",
        "build_futures_branch_closure_evidence_pack",
        "FUTURES_BRANCH_CLOSURE_CONFIRMED",
        "HYPOTHESIS_BRANCH_CLOSED_NO_GO",
        "FINAL_25F_BRANCH_CLOSED_NO_GO",
        "PRIMARY_TERMINAL_AUDIT_BLOCK_CONFIRMED",
        "COMPANION_TERMINAL_AUDIT_BLOCK_CONFIRMED",
        "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        "approved_for_live_real",
        "post_requests_allowed",
    ],
    "tools/run_futures_branch_closure_evidence_pack_4B436625H.py": [
        "__input_json",
        "__reports_dir",
        "__include_all",
        "__hypothesis_id",
        "__review_ok",
        "futures branch closure evidence pack",
    ],
    "tests/test_futures_branch_closure_evidence_pack_4B436625H.py": [
        "test_closure_pack_confirms_closed_no_go_from_final_25f_and_terminal_blocks",
        "test_closure_pack_blocks_when_final_25f_missing",
        "test_tool_writes_closure_report_from_input_json",
    ],
    "docs/FUTURES_BRANCH_CLOSURE_EVIDENCE_PACK_RUNBOOK_4B436625H.md": [
        "Futures Branch Closure Evidence Pack",
        "HYP-002",
        "BRANCH_CLOSED_NO_GO",
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
    print("4B.4.3.6.6.25H futures branch closure evidence pack patch applied")
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
        comparable = text.replace("-", "_").replace(" ", "_")
        for marker in markers:
            present = marker.replace("-", "_").replace(" ", "_") in comparable
            print(f" - {marker.replace('-', '_').replace(' ', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
