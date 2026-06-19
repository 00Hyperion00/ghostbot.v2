from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/replay_gate.py",
    "tests/test_replay_backtest_walkforward_gate_4B436629D.py",
    "tools/apply_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/check_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/run_4B436629D_replay_backtest_walkforward_gate.py",
    "tools/rollback_4B436629D_replay_backtest_walkforward_gate.py",
    "docs/REPLAY_BACKTEST_WALKFORWARD_GATE_4B436629D.md",
]


def main() -> int:
    root = Path.cwd()
    for rel in FILES:
        path = root / rel
        if path.exists():
            path.unlink()
    print("4B.4.3.6.6.29D replay/backtest/walk-forward gate files removed; config fields are left for manual review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
