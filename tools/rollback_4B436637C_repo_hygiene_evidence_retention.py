from __future__ import annotations

import json
from pathlib import Path

PATCH_FILES = [
    "README_APPLY_4B436637C.txt",
    "docs/REPO_HYGIENE_EVIDENCE_RETENTION_4B436637C.md",
    "src/tradebot/repo_hygiene_evidence_retention.py",
    "tests/test_repo_hygiene_evidence_retention_4B436637C.py",
    "tools/check_4B436637C_repo_hygiene_evidence_retention.py",
    "tools/run_4B436637C_repo_hygiene_evidence_retention.py",
    "tools/rollback_4B436637C_repo_hygiene_evidence_retention.py",
]


def main() -> int:
    removed: list[str] = []
    for rel in PATCH_FILES:
        path = Path(rel)
        if path.exists():
            path.unlink()
            removed.append(rel)
    print(json.dumps({
        "rolled_back": True,
        "patch_id": "4B436637C",
        "removed_files": removed,
        "report_delete_performed": False,
        "archive_move_performed": False,
        "destructive_cleanup_performed": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
