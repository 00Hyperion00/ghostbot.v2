from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS: list[tuple[str, bool]] = []


def _exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def _contains(relative: str, needle: str) -> bool:
    path = ROOT / relative
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8", errors="ignore")


def _py_compile(relative: str) -> bool:
    try:
        py_compile.compile(str(ROOT / relative), doraise=True)
    except Exception:
        return False
    return True


def main() -> int:
    files = [
        "src/tradebot/research_hyp005_shadow_quality_audit.py",
        "tools/run_hyp005_shadow_quality_audit_4B436625AB.py",
        "tests/test_hyp005_shadow_quality_audit_4B436625AB.py",
        "docs/HYP005_SHADOW_QUALITY_AUDIT_4B436625AB.md",
    ]
    for relative in files:
        CHECKS.append((f"{relative}_exists", _exists(relative)))
        if relative.endswith(".py"):
            CHECKS.append((f"{relative}_py_compile_ok", _py_compile(relative)))

    markers = [
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "HYP005_SHADOW_QUALITY_CONTRACT_VERSION"),
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED"),
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING"),
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "SHADOW_SLIPPAGE_PROXY_HIGH"),
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "approved_for_live_real"),
        ("src/tradebot/research_hyp005_shadow_quality_audit.py", "post_requests_allowed"),
        ("tools/run_hyp005_shadow_quality_audit_4B436625AB.py", "--reports-dir"),
        ("tools/run_hyp005_shadow_quality_audit_4B436625AB.py", "--include-all"),
        ("tests/test_hyp005_shadow_quality_audit_4B436625AB.py", "test_maturity_pending_not_counted_as_true_missing_field"),
        ("tests/test_hyp005_shadow_quality_audit_4B436625AB.py", "test_tool_writes_quality_audit_report"),
        ("docs/HYP005_SHADOW_QUALITY_AUDIT_4B436625AB.md", "Shadow Observation Quality"),
    ]
    for relative, needle in markers:
        CHECKS.append((f"{needle}_present", _contains(relative, needle)))

    print("4B.4.3.6.6.25AB HYP-005 shadow quality/slippage audit patch applied")
    for key, ok in CHECKS:
        print(f" - {key}: {ok}")
    return 0 if all(ok for _, ok in CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
