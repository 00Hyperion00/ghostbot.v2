from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tools/run_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tools/apply_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tools/check_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tools/rollback_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tests/test_hyp006_no_order_overlay_simulation_bnbusdt_4B436628G_H7.py",
    "docs/HYP006_R1_NO_ORDER_OVERLAY_SIMULATION_BNBUSDT_4B436628G_H7.md",
    "README_APPLY_4B436628G_H7.txt",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    removed = 0
    for name in FILES:
        path = root / name
        if path.exists():
            path.unlink()
            removed += 1
            print(f"removed: {name}")
    print(f"4B.4.3.6.6.28G-H7 rollback complete; removed={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
