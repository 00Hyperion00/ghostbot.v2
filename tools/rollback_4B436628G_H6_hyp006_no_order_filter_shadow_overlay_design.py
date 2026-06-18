from __future__ import annotations

from pathlib import Path

FILES = [
    "src/tradebot/hyp006_no_order_filter_shadow_overlay_design.py",
    "tools/run_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py",
    "tools/apply_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py",
    "tools/check_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py",
    "tools/rollback_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py",
    "tests/test_hyp006_no_order_filter_shadow_overlay_design_4B436628G_H6.py",
    "docs/HYP006_R1_NO_ORDER_FILTER_SHADOW_OVERLAY_DESIGN_4B436628G_H6.md",
    "README_APPLY_4B436628G_H6.txt",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    removed: list[str] = []
    for rel in FILES:
        target = root / rel
        if target.exists():
            target.unlink()
            removed.append(rel)
    print("4B.4.3.6.6.28G-H6 rollback removed files:")
    for rel in removed:
        print(f" - {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
