from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp004_branch_closure_evidence_pack.py", [
        "HYP004_BRANCH_CLOSURE_CONTRACT_VERSION",
        "Hyp004ClosureLimits",
        "build_hyp004_branch_closure_evidence_pack",
        "HYP004_BRANCH_CLOSURE_CONFIRMED",
        "HYP004_EXPLORATION_BLOCK_CONFIRMED",
        "HYP004_REFINEMENT_BLOCK_CONFIRMED",
        "NO_HYP004_REFINED_RELATIVE_STRENGTH_CANDIDATE_PASSED_CONFIRMED",
        "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp004_branch_closure_evidence_pack_4B436625Q.py", [
        "__input_json",
        "__reports_dir",
        "__include_all",
        "__hypothesis_id",
        "__review_ok",
        "registry_snapshot_json",
    ]),
    ("tests/test_hyp004_branch_closure_evidence_pack_4B436625Q.py", [
        "test_25q_confirms_hyp004_closure_from_25o_25p_blocks",
        "test_25q_blocks_when_25p_refinement_missing",
        "test_tool_writes_closure_report_and_registry_snapshot",
    ]),
    ("docs/HYP004_BRANCH_CLOSURE_EVIDENCE_PACK_RUNBOOK_4B436625Q.md", [
        "HYP-004 Branch Closure Evidence Pack",
        "HYP004_BRANCH_CLOSURE_CONFIRMED",
        "Training remains blocked",
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
    print("4B.4.3.6.6.25Q HYP-004 branch closure evidence pack patch applied")
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
        normalized = text.replace("-", "_").replace(" ", "_")
        for marker in markers:
            present = marker.replace("-", "_").replace(" ", "_") in normalized
            print(f" - {marker.replace('-', '_').replace(' ', '_')}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
