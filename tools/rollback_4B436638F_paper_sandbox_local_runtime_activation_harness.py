from __future__ import annotations

import json


def main() -> int:
    result = {
        "patch_id": "4B436638F",
        "patch_version": "4B.4.3.6.6.38F",
        "rollback_supported": False,
        "reason": "Patch is additive and no destructive runtime/report/git mutation is performed.",
        "file_delete_performed": False,
        "file_move_performed": False,
        "report_delete_performed": False,
        "git_reset_performed": False,
        "runtime_start_performed": False,
        "order_submit_performed": False,
        "network_request_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
