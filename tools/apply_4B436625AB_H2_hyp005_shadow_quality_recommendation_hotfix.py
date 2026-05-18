from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS: list[tuple[str, bool]] = []


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _py_compile(rel: str) -> bool:
    path = ROOT / rel
    if not path.exists():
        return False
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _contains(rel: str, text: str) -> bool:
    path = ROOT / rel
    if not path.exists():
        return False
    return text in path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    files = [
        "src/tradebot/research_hyp005_shadow_quality_audit.py",
        "tools/run_hyp005_shadow_quality_audit_4B436625AB.py",
        "tests/test_hyp005_shadow_quality_audit_hotfix_25ABH2.py",
        "docs/HYP005_SHADOW_QUALITY_AUDIT_RECOMMENDATION_HOTFIX_25ABH2.md",
    ]
    for rel in files:
        CHECKS.append((f"{rel}_exists", _exists(rel)))
    for rel in [
        "src/tradebot/research_hyp005_shadow_quality_audit.py",
        "tools/run_hyp005_shadow_quality_audit_4B436625AB.py",
        "tests/test_hyp005_shadow_quality_audit_hotfix_25ABH2.py",
    ]:
        CHECKS.append((f"{rel}_py_compile_ok", _py_compile(rel)))

    markers = [
        ("HYP005_SHADOW_QUALITY_HOTFIX_VERSION_present", "HYP005_SHADOW_QUALITY_HOTFIX_VERSION"),
        ("25AB_H2_present", "4B.4.3.6.6.25AB-H2"),
        ("RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED_present", "RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED"),
        ("BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION_present", "BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION"),
        ("_build_quality_audit_recommendation_present", "def _build_quality_audit_recommendation"),
        ("recommendation_consistency_report_field_present", '"recommendation_consistency"'),
        ("no_unique_observation_claim_allowed_present", "no_unique_observation_claim_allowed"),
        ("25AB_H1_backward_compat_report_present", "4B436625AB_H1_hyp005_shadow_quality_slippage_audit_"),
        ("25AB_legacy_report_present", "4B436625AB_hyp005_shadow_quality_slippage_audit_"),
        ("no_order_guardrail_present", "post_requests_allowed"),
    ]
    for name, marker in markers:
        CHECKS.append((name, _contains("src/tradebot/research_hyp005_shadow_quality_audit.py", marker)))

    test_markers = [
        "test_25abh2_block_with_unique_observations_does_not_claim_no_unique_obs",
        "test_25abh2_no_observations_keeps_no_unique_observation_recommendation",
        "test_25abh2_tool_writes_h2_and_backward_compatible_reports",
        "test_25abh2_no_order_guardrails_remain_closed",
    ]
    for marker in test_markers:
        CHECKS.append((f"{marker}_present", _contains("tests/test_hyp005_shadow_quality_audit_hotfix_25ABH2.py", marker)))

    doc_markers = [
        "Recommendation Message Consistency Hotfix",
        "unique shadow observations",
        "Paper/live remain blocked",
    ]
    for marker in doc_markers:
        CHECKS.append((f"docs_{marker.replace(' ', '_')}_present", _contains("docs/HYP005_SHADOW_QUALITY_AUDIT_RECOMMENDATION_HOTFIX_25ABH2.md", marker)))

    print("4B.4.3.6.6.25AB-H2 HYP-005 shadow quality recommendation message consistency hotfix applied")
    ok = True
    for name, passed in CHECKS:
        print(f" - {name}: {passed}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
