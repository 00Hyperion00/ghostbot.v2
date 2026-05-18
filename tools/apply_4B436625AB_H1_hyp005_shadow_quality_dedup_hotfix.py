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
        "tests/test_hyp005_shadow_quality_audit_hotfix_25ABH1.py",
        "docs/HYP005_SHADOW_QUALITY_AUDIT_DEDUP_HOTFIX_25ABH1.md",
    ]
    for rel in files:
        CHECKS.append((f"{rel}_exists", _exists(rel)))
    for rel in [
        "src/tradebot/research_hyp005_shadow_quality_audit.py",
        "tools/run_hyp005_shadow_quality_audit_4B436625AB.py",
        "tests/test_hyp005_shadow_quality_audit_hotfix_25ABH1.py",
    ]:
        CHECKS.append((f"{rel}_py_compile_ok", _py_compile(rel)))

    markers = [
        ("HYP005_SHADOW_QUALITY_HOTFIX_VERSION_present", "HYP005_SHADOW_QUALITY_HOTFIX_VERSION"),
        ("25AB_H1_present", "4B.4.3.6.6.25AB-H1"),
        ("_canonical_observation_key_present", "def _canonical_observation_key"),
        ("canonical_dedupe_strategy_present", "hypothesis_id|strategy_family|symbol|timeframe|timestamp_utc"),
        ("_dedupe_observations_with_stats_present", "def _dedupe_observations_with_stats"),
        ("OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED_present", "OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED"),
        ("OBSERVATION_DUPLICATES_REMOVED_present", "OBSERVATION_DUPLICATES_REMOVED"),
        ("deduplication_report_field_present", '"deduplication"'),
        ("preferred_duplicate_policy_present", "prefer_matured_forward_return_then_data_quality_then_fewer_missing_fields"),
        ("no_order_guardrail_present", "post_requests_allowed"),
    ]
    for name, marker in markers:
        CHECKS.append((name, _contains("src/tradebot/research_hyp005_shadow_quality_audit.py", marker)))

    test_markers = [
        "test_25abh1_canonical_dedupes_rolling_row_index_duplicates",
        "test_25abh1_prefers_matured_duplicate_over_pending_duplicate",
        "test_25abh1_jsonl_wrapper_rows_are_not_counted_as_observations",
        "test_25abh1_tool_writes_deduped_report",
    ]
    for marker in test_markers:
        CHECKS.append((f"{marker}_present", _contains("tests/test_hyp005_shadow_quality_audit_hotfix_25ABH1.py", marker)))

    doc_markers = [
        "Deduplication Hotfix",
        "canonical observation key",
        "Paper/live remain blocked",
    ]
    for marker in doc_markers:
        CHECKS.append((f"docs_{marker.replace(' ', '_')}_present", _contains("docs/HYP005_SHADOW_QUALITY_AUDIT_DEDUP_HOTFIX_25ABH1.md", marker)))

    print("4B.4.3.6.6.25AB-H1 HYP-005 shadow quality audit deduplication hotfix applied")
    ok = True
    for name, passed in CHECKS:
        print(f" - {name}: {passed}")
        ok = ok and passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
