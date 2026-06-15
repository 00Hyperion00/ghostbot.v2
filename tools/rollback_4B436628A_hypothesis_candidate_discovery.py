from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATED = [
    ROOT / "src" / "tradebot" / "hypothesis_candidate_discovery.py",
    ROOT / "tools" / "run_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "check_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "apply_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tools" / "rollback_4B436628A_hypothesis_candidate_discovery.py",
    ROOT / "tests" / "test_hypothesis_candidate_discovery_4B436628A.py",
    ROOT / "docs" / "NEW_HYPOTHESIS_CANDIDATE_DISCOVERY_4B436628A.md",
    ROOT / "README_APPLY_4B436628A.txt",
]


def main() -> int:
    removed = []
    for path in CREATED:
        if path.exists():
            path.unlink()
            removed.append(str(path.relative_to(ROOT)))
    print("4B.4.3.6.6.28A hypothesis candidate discovery rollback completed")
    for item in removed:
        print(f" - removed: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
