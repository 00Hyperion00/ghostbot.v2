from __future__ import annotations

from pathlib import Path

FILES = ['README_APPLY_4B436630T.txt', 'docs/PAPER_SOAK_EVIDENCE_WINDOW_4B436630T.md', 'src/tradebot/paper_soak_evidence_window.py', 'tests/test_paper_soak_evidence_window_4B436630T.py', 'tools/apply_4B436630T_paper_soak_evidence_window.py', 'tools/check_4B436630T_paper_soak_evidence_window.py', 'tools/rollback_4B436630T_paper_soak_evidence_window.py', 'tools/run_4B436630T_paper_soak_evidence_window.py']


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30T rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
