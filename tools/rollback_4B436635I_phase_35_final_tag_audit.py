from __future__ import annotations

import json
from pathlib import Path

PATCH_FILES = [
    "README_APPLY_4B436635I.txt",
    "docs/PHASE_35_FINAL_TAG_AUDIT_4B436635I.md",
    "src/tradebot/phase_35_final_tag_audit.py",
    "tests/test_phase_35_final_tag_audit_4B436635I.py",
    "tools/check_4B436635I_phase_35_final_tag_audit.py",
    "tools/run_4B436635I_phase_35_final_tag_audit.py",
    "tools/rollback_4B436635I_phase_35_final_tag_audit.py",
]


def main() -> int:
    removed: list[str] = []
    skipped: list[str] = []
    for rel_path in PATCH_FILES:
        path = Path(rel_path)
        if path.exists() and path.is_file():
            path.unlink()
            removed.append(rel_path)
        else:
            skipped.append(rel_path)
    print(json.dumps({"rolled_back": True, "removed_files": removed, "skipped_files": skipped}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
