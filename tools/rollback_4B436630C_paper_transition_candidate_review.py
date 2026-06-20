from __future__ import annotations

from pathlib import Path

FILES = (
    "docs/PAPER_TRANSITION_CANDIDATE_REVIEW_4B436630C.md",
    "src/tradebot/paper_transition_candidate_review.py",
    "tests/test_paper_transition_candidate_review_4B436630C.py",
    "tools/apply_4B436630C_paper_transition_candidate_review.py",
    "tools/check_4B436630C_paper_transition_candidate_review.py",
    "tools/run_4B436630C_paper_transition_candidate_review.py",
    "tools/rollback_4B436630C_paper_transition_candidate_review.py",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            print(f"removed {rel}")
    print("4B.4.3.6.6.30C rollback completed. Config field removal is intentionally manual to avoid unsafe automated edits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
