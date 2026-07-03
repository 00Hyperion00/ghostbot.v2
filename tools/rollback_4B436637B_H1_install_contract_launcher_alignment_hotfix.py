from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436637B-H1"
PATCH_ID_COMPACT = "4B436637B_H1"
PATCH_VERSION = "4B.4.3.6.6.37B-H1"
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    backups = sorted((ROOT / "tools").glob(f"_patch_backup_{PATCH_ID_COMPACT}_*"))
    latest = backups[-1] if backups else None
    result = {
        "patch_id": PATCH_ID_COMPACT,
        "patch_version": PATCH_VERSION,
        "rollback_available": latest is not None,
        "latest_backup_root": str(latest.relative_to(ROOT)) if latest else None,
        "rollback_performed": False,
        "manual_restore_required": latest is not None,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "network_request_performed": False,
        "file_delete_performed": False,
        "destructive_cleanup_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
