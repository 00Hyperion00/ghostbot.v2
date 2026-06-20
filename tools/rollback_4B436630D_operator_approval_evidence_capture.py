from __future__ import annotations

from pathlib import Path

FILES = [
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D.md",
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D.py",
    "tools/apply_4B436630D_operator_approval_evidence_capture.py",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
    "tools/rollback_4B436630D_operator_approval_evidence_capture.py",
]


def main() -> int:
    root = Path.cwd().resolve()
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            print(f"removed {rel}")
    print("config.py field rollback is intentionally manual to avoid removing adjacent accepted 30A-30C fields")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
