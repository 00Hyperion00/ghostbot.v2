from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: list[tuple[str, Path, str | None]] = [
    ("src/tradebot/research_hyp005_shadow_acceptance_readiness.py_exists", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", None),
    ("HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION"),
    ("Hyp005ShadowAcceptanceLimits_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "Hyp005ShadowAcceptanceLimits"),
    ("ShadowAcceptanceSummary_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "ShadowAcceptanceSummary"),
    ("build_hyp005_shadow_acceptance_report_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "build_hyp005_shadow_acceptance_report"),
    ("HYP005_SHADOW_PAPER_TRANSITION_READY_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "HYP005_SHADOW_PAPER_TRANSITION_READY"),
    ("HYP005_SHADOW_PAPER_TRANSITION_BLOCK_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"),
    ("PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT"),
    ("NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"),
    ("approved_for_live_real_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "approved_for_live_real"),
    ("post_requests_allowed_present", ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py", "post_requests_allowed"),
    ("tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py_exists", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", None),
    ("__ledger_json_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__ledger_json"),
    ("__ledger_jsonl_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__ledger_jsonl"),
    ("__input_json_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__input_json"),
    ("__reports_dir_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__reports_dir"),
    ("__include_all_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__include_all"),
    ("__review_ok_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "__review_ok"),
    ("paper_transition_readiness_only_present", ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "paper_transition_readiness_only"),
    ("tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py_exists", ROOT / "tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py", None),
    ("test_25w_blocks_empty_shadow_ledger_present", ROOT / "tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py", "test_25w_blocks_empty_shadow_ledger"),
    ("test_25w_accepts_strong_shadow_ledger_but_keeps_paper_live_blocked_present", ROOT / "tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py", "test_25w_accepts_strong_shadow_ledger_but_keeps_paper_live_blocked"),
    ("test_tool_writes_report_and_summary_from_ledger_json_present", ROOT / "tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py", "test_tool_writes_report_and_summary_from_ledger_json"),
    ("docs/HYP005_SHADOW_ACCEPTANCE_READINESS_RUNBOOK_4B436625W.md_exists", ROOT / "docs/HYP005_SHADOW_ACCEPTANCE_READINESS_RUNBOOK_4B436625W.md", None),
    ("HYP_005_Shadow_Observation_Acceptance_present", ROOT / "docs/HYP005_SHADOW_ACCEPTANCE_READINESS_RUNBOOK_4B436625W.md", "HYP-005 Shadow Observation Acceptance"),
    ("Paper_transition_readiness_is_not_paper_permission_present", ROOT / "docs/HYP005_SHADOW_ACCEPTANCE_READINESS_RUNBOOK_4B436625W.md", "Paper-transition readiness is not paper permission"),
]


def compile_file(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    print("4B.4.3.6.6.25W HYP-005 shadow observation acceptance / paper-transition readiness patch applied")
    for label, path, marker in CHECKS:
        if marker is None:
            ok = path.exists()
        else:
            ok = path.exists() and marker in path.read_text(encoding="utf-8")
        print(f" - {label}: {ok}")
    for path in (
        ROOT / "src/tradebot/research_hyp005_shadow_acceptance_readiness.py",
        ROOT / "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py",
        ROOT / "tests/test_hyp005_shadow_acceptance_readiness_4B436625W.py",
    ):
        print(f" - {path.relative_to(ROOT)}_py_compile_ok: {compile_file(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
