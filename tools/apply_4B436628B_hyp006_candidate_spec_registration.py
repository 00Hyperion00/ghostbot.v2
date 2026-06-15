from __future__ import annotations

import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28B"
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    ROOT / "src" / "tradebot" / "hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "run_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "check_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tools" / "rollback_4B436628B_hyp006_candidate_spec_registration.py",
    ROOT / "tests" / "test_hyp006_candidate_spec_registration_4B436628B.py",
    ROOT / "docs" / "HYP006_R1_CANDIDATE_SPEC_REGISTRATION_4B436628B.md",
]


def _compile(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    files_present = all(path.exists() for path in EXPECTED)
    py_compile_ok = all(_compile(path) for path in EXPECTED if path.suffix == ".py")
    module_text = (ROOT / "src" / "tradebot" / "hyp006_candidate_spec_registration.py").read_text(encoding="utf-8")
    runner_text = (ROOT / "tools" / "run_4B436628B_hyp006_candidate_spec_registration.py").read_text(encoding="utf-8")
    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "all_expected_files_present": files_present,
        "all_py_compile_ok": py_compile_ok,
        "contract_version_present": CONTRACT_VERSION in module_text,
        "hyp006_candidate_spec_present": "HYP-006-R1" in module_text and "CandidateSpecDraft" in module_text,
        "registration_gate_present": "approved_for_no_order_shadow_registration_candidate" in module_text,
        "runner_requires_review_ok": "--review-ok" in runner_text and "REVIEW_OK_REQUIRED" in runner_text,
        "requires_28c_gate_present": "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN" in module_text,
        "shadow_collection_blocked": "approved_for_shadow_collection\": False" in module_text,
        "paper_live_order_enablement_present": False,
    }
    print(f"{CONTRACT_VERSION} HYP-006-R1 Candidate Spec Draft / No-Order Shadow Registration Gate patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    positive = {key: value for key, value in checks.items() if key not in {"config_mutation_performed", "scheduler_mutation_performed", "training_performed", "reload_performed", "trading_action_performed", "paper_live_order_enablement_present"}}
    return 0 if all(positive.values()) and not checks["paper_live_order_enablement_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
