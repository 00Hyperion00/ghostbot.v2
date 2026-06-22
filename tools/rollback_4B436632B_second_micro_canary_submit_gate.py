from __future__ import annotations

import json
from pathlib import Path

FILES = [
    "src/tradebot/second_micro_canary_submit_gate.py",
    "tools/check_4B436632B_second_micro_canary_submit_gate.py",
    "tools/run_4B436632B_second_micro_canary_submit_gate.py",
    "tools/apply_4B436632B_second_micro_canary_submit_gate.py",
    "tools/rollback_4B436632B_second_micro_canary_submit_gate.py",
    "tests/test_second_micro_canary_submit_gate_4B436632B.py",
    "docs/SECOND_MICRO_CANARY_SUBMIT_GATE_4B436632B.md",
]


def main() -> int:
    root = Path.cwd().resolve()
    removed: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
        removed[rel] = not path.exists()
    print(json.dumps({"ok": all(removed.values()), "removed": removed, "patch_network_submit_attempted": False}, indent=2, sort_keys=True))
    return 0 if all(removed.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
