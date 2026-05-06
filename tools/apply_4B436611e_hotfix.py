from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src" / "tradebot" / "ui" / "dashboard.py"


def main() -> None:
    text = DASHBOARD.read_text(encoding="utf-8")
    before_count = text.count("safe_obj_safe_obj_getattr")
    if before_count:
        text = text.replace("safe_obj_safe_obj_getattr", "safe_obj_getattr")
        DASHBOARD.write_text(text, encoding="utf-8")

    after_count = text.count("safe_obj_safe_obj_getattr")
    print("4B.4.3.6.6.11e hotfix applied")
    print(f" - dashboard.safe_obj_safe_obj_getattr_replaced: {before_count}")
    print(f" - dashboard.remaining_double_safe_getattr: {after_count}")


if __name__ == "__main__":
    main()
