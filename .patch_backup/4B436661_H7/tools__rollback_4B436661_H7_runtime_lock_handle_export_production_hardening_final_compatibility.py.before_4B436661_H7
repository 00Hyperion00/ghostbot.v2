from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    print(json.dumps({
        "patch_id": "4B436661_H7",
        "rollback_available": False,
        "manual_restore_from_patch_backup_required": True,
        "backup_dir_hint": str(Path(".patch_backup") / "4B436661_H7"),
        "file_delete_performed": False,
        "file_move_performed": False,
        "runtime_start_performed": False,
        "network_request_performed": False,
        "exchange_submit_performed": False,
        "paper_submit_performed": False,
        "ok": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
