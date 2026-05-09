from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("src/tradebot/research_hyp005_no_order_shadow_planning.py", [
        "HYP005_SHADOW_PLANNING_CONTRACT_VERSION",
        "Hyp005NoOrderShadowCandidateSpec",
        "Hyp005ShadowPlanningLimits",
        "ShadowAcceptanceMetric",
        "build_hyp005_no_order_shadow_planning_report",
        "HYP005_SHADOW_PLAN_READY",
        "HYP005_SHADOW_PLAN_BLOCK",
        "NO_ORDER_SHADOW_ONLY",
        "paper_transition_requires_new_gate",
        "live_transition_requires_separate_gate",
        "approved_for_live_real",
        "post_requests_allowed",
    ]),
    ("tools/run_hyp005_no_order_shadow_planning_4B436625U.py", [
        "__input_json",
        "__reports_dir",
        "__include_all",
        "__review_ok",
        "candidate_spec_json",
        "no_order_shadow_only",
        "HYP-005 no-order shadow planning",
    ]),
    ("tests/test_hyp005_no_order_shadow_planning_4B436625U.py", [
        "test_validate_hyp005_25s_and_25t_pass_chain",
        "test_25u_builds_no_order_shadow_plan_and_candidate_spec",
        "test_25u_blocks_when_robustness_missing_or_not_pass",
        "test_tool_writes_report_and_candidate_spec_json",
        "HYP005_SHADOW_PLAN_READY",
    ]),
    ("docs/HYP005_NO_ORDER_SHADOW_PLANNING_RUNBOOK_4B436625U.md", [
        "HYP-005 No-Order Shadow Planning",
        "HYP005_SHADOW_PLAN_READY",
        "Candidate spec is not trading permission",
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
    print("4B.4.3.6.6.25U HYP-005 no-order shadow planning / candidate spec gate patch applied")
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
            present = marker in text
            safe = marker.replace("-", "_").replace(" ", "_").replace("/", "_")
            print(f" - {safe}_present: {present}")
            ok = ok and present
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
