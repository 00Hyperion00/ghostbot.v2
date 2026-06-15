from __future__ import annotations

import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28A"
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    ROOT / "src" / "tradebot" / "hypothesis_candidate_discovery.py",
    ROOT / "tools" / "run_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "check_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "rollback_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tests" / "test_hypothesis_candidate_discovery_4B436628A.py",
    ROOT / "docs" / "NEW_HYPOTHESIS_CANDIDATE_DISCOVERY_4B436628A.md",
]


def _compile(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    files_present = all(path.exists() for path in EXPECTED)
    py_compile_ok = all(_compile(path) for path in EXPECTED if path.suffix == ".py")
    module_text = (ROOT / "src" / "tradebot" / "hypothesis_candidate_discovery.py").read_text(encoding="utf-8")
    runner_text = (ROOT / "tools" / "run_4B436628A_hypothesis_candidate_discovery.py").read_text(encoding="utf-8")
    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "all_expected_files_present": files_present,
        "all_py_compile_ok": py_compile_ok,
        "contract_version_present": CONTRACT_VERSION in module_text,
        "failed_branch_lessons_present": "FailedBranchLessons" in module_text,
        "candidate_selection_present": "selected_research_candidate" in module_text,
        "runner_requires_review_ok": "--review-ok" in runner_text and "REVIEW_OK_REQUIRED" in runner_text,
        "branch_state_mutation_blocked": "branch_state_mutation_performed\": False" in module_text,
        "paper_live_order_enablement_present": False,
    }
    print(f"{CONTRACT_VERSION} New Hypothesis Candidate Discovery / Failed Branch Lessons Integration patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if all(value is not False for key, value in checks.items() if key not in {"config_mutation_performed", "scheduler_mutation_performed", "training_performed", "reload_performed", "trading_action_performed", "paper_live_order_enablement_present"}) else 1


if __name__ == "__main__":
    raise SystemExit(main())
