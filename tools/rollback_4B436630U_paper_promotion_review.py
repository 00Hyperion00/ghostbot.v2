from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630U.txt",
    "docs/PAPER_PROMOTION_REVIEW_4B436630U.md",
    "src/tradebot/paper_promotion_review.py",
    "tests/test_paper_promotion_review_4B436630U.py",
    "tools/apply_4B436630U_paper_promotion_review.py",
    "tools/check_4B436630U_paper_promotion_review.py",
    "tools/rollback_4B436630U_paper_promotion_review.py",
    "tools/run_4B436630U_paper_promotion_review.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30U paper promotion review files removed; config fields left for manual cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
