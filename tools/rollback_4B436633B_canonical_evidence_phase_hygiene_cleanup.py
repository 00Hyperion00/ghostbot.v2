from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436633B"
PATCH_VERSION = "4B.4.3.6.6.33B"
WRITTEN_FILES = ['README_APPLY_4B436633B.txt', 'docs/CANONICAL_EVIDENCE_PHASE_HYGIENE_CLEANUP_4B436633B.md', 'src/tradebot/canonical_evidence_phase_hygiene.py', 'tests/test_canonical_evidence_phase_hygiene_4B436633B.py', 'tools/check_4B436633B_canonical_evidence_phase_hygiene_cleanup.py', 'tools/run_4B436633B_canonical_evidence_phase_hygiene_cleanup.py']


def main() -> int:
    repo_root = Path.cwd()
    removed: list[str] = []
    missing: list[str] = []
    for relative in WRITTEN_FILES:
        path = repo_root / relative
        if path.exists():
            path.unlink()
            removed.append(relative)
        else:
            missing.append(relative)
    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "rolled_back": True,
        "removed_files": removed,
        "missing_files": missing,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
