from __future__ import annotations

from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30D-H2"
FILES = [
    "README_APPLY_4B436630D_H2.txt",
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D_H2.md",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H2.py",
    "tools/apply_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/check_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/rollback_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    removed: list[str] = []
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(f"{CONTRACT_VERSION} rollback removed H2 metadata files only")
    for rel in removed:
        print(f" - removed: {rel}")
    print("NOTE: this rollback does not restore tracked _patch_payload artifacts or remove the report collision guard patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
