from __future__ import annotations

import json
from pathlib import Path

PATCH_ID = "4B436639B"
PATCH_VERSION = "4B.4.3.6.6.39B"
PATCH_NAME = "Paper Sandbox Runtime Start Command Contract"
REMOVABLE_FILES = [
    "README_APPLY_4B436639B.txt",
    "docs/PAPER_SANDBOX_RUNTIME_START_COMMAND_CONTRACT_4B436639B.md",
    "src/tradebot/paper_sandbox_runtime_start_command_contract.py",
    "tests/test_paper_sandbox_runtime_start_command_contract_4B436639B.py",
    "tools/apply_4B436639B_paper_sandbox_runtime_start_command_contract.py",
    "tools/check_4B436639B_paper_sandbox_runtime_start_command_contract.py",
    "tools/run_4B436639B_paper_sandbox_runtime_start_command_contract.py",
    "tools/rollback_4B436639B_paper_sandbox_runtime_start_command_contract.py",
]


def main() -> int:
    removed: list[str] = []
    missing: list[str] = []
    for file_name in REMOVABLE_FILES:
        path = Path(file_name)
        if path.exists():
            path.unlink()
            removed.append(file_name)
        else:
            missing.append(file_name)
    result = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "rollback_performed": True,
        "removed_files": removed,
        "missing_files": missing,
        "approved_for_paper_transition": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "runtime_start_command_executed": False,
        "runtime_start_performed": False,
        "network_order_submit_performed": False,
        "exchange_submit_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
