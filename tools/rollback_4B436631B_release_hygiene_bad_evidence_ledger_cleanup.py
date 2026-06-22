from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "src/tradebot/release_hygiene_bad_evidence_cleanup.py",
    "tests/test_release_hygiene_bad_evidence_cleanup_4B436631B.py",
    "tools/run_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py",
    "tools/check_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py",
    "tools/apply_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py",
    "tools/rollback_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py",
    "docs/RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_4B436631B.md",
    "README_APPLY_4B436631B.txt",
]


def main() -> int:
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = Path(rel)
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    print(json.dumps({"ok": all(removed.values()), "removed": removed}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
