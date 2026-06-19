from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/run_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/apply_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/check_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tools/rollback_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
    "tests/test_hyp006_bnbusdt_overlay_oos_evaluation_4B436628G_H8.py",
    "docs/HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_4B436628G_H8.md",
    "README_APPLY_4B436628G_H8.txt",
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
    print(f"4B.4.3.6.6.28G-H8 rollback complete; removed={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
