from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630S.txt",
    "docs/PAPER_MODE_RUNTIME_GUARDRAIL_4B436630S.md",
    "src/tradebot/paper_mode_runtime_guardrail.py",
    "tests/test_paper_mode_runtime_guardrail_4B436630S.py",
    "tools/apply_4B436630S_paper_mode_runtime_guardrail.py",
    "tools/check_4B436630S_paper_mode_runtime_guardrail.py",
    "tools/rollback_4B436630S_paper_mode_runtime_guardrail.py",
    "tools/run_4B436630S_paper_mode_runtime_guardrail.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30S rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
