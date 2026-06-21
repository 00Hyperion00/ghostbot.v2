from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630V.txt",
    "docs/LIVE_REAL_PREFLIGHT_GATE_4B436630V.md",
    "src/tradebot/live_real_preflight_gate.py",
    "tests/test_live_real_preflight_gate_4B436630V.py",
    "tools/apply_4B436630V_live_real_preflight_gate.py",
    "tools/check_4B436630V_live_real_preflight_gate.py",
    "tools/rollback_4B436630V_live_real_preflight_gate.py",
    "tools/run_4B436630V_live_real_preflight_gate.py",
]


def main() -> int:
    for rel in FILES:
        Path(rel).unlink(missing_ok=True)
    print("4B.4.3.6.6.30V live-real preflight gate files removed; config fields left for manual cleanup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
