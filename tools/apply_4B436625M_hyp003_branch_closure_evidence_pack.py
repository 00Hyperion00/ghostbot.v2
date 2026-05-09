from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp003_branch_closure_evidence_pack.py", [
        "HYP003_BRANCH_CLOSURE_CONTRACT_VERSION",
        "Hyp003ClosureLimits",
        "build_hyp003_branch_closure_evidence_pack",
        "HYP003_BRANCH_CLOSURE_CONFIRMED",
        "HYP003_ROBUSTNESS_BLOCK_CONFIRMED",
        "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED",
        "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp003_branch_closure_evidence_pack_4B436625M.py", [
        "__input_json",
        "__reports_dir",
        "__include_all",
        "__hypothesis_id",
        "__review_ok",
        "registry_snapshot_json",
    ]),
    ("tests/test_hyp003_branch_closure_evidence_pack_4B436625M.py", [
        "test_25m_confirms_hyp003_branch_closure_from_25j_25k_25l",
        "test_25m_blocks_when_25l_closure_missing",
        "test_tool_writes_closure_report_and_registry_snapshot",
    ]),
    ("docs/HYP003_BRANCH_CLOSURE_EVIDENCE_PACK_RUNBOOK_4B436625M.md", [
        "HYP-003 Branch Closure Evidence Pack",
        "HYP003_BRANCH_CLOSURE_CONFIRMED",
        "Paper/live remain blocked",
    ]),
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f" - {path}_py_compile_error: {exc}")
        return False


def main() -> int:
    print("4B.4.3.6.6.25M HYP-003 branch closure evidence pack patch applied")
    ok = True
    for rel, markers in CHECKS:
        path = ROOT / rel
        exists = path.exists()
        print(f" - {rel}_exists: {exists}")
        ok = ok and exists
        if exists and path.suffix == ".py":
            compiled = _compile(path)
            print(f" - {rel}_py_compile_ok: {compiled}")
            ok = ok and compiled
        text = path.read_text(encoding="utf-8") if exists else ""
        for marker in markers:
            present = marker.replace("-", "_") in text.replace("-", "_")
            safe = marker.replace("-", "_").replace(" ", "_")
            print(f" - {safe}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
