from __future__ import annotations

import json


def main() -> int:
    result = {
        "patch_id": "4B436635C",
        "patch_version": "4B.4.3.6.6.35C",
        "rollback_available": False,
        "rollback_status": "NO_BACKUP_CREATED_EXPAND_ARCHIVE_OVERLAY_ONLY",
        "destructive_cleanup_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
