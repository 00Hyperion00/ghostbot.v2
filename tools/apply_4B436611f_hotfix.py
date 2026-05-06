from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'


def main() -> None:
    text = DASHBOARD.read_text(encoding='utf-8')
    before = text.count("getattr(self, 'btn_balance_sync', None)")
    text = text.replace(
        "getattr(self, 'btn_balance_sync', None)",
        "safe_obj_getattr(self, 'btn_balance_sync', None)",
    )
    # Defensive cleanup in case a prior script left any double-safe typo behind.
    double_before = text.count('safe_obj_safe_obj_getattr')
    text = text.replace('safe_obj_safe_obj_getattr', 'safe_obj_getattr')
    # Defensive conversion for any remaining dashboard button getattr calls in the same control surface.
    button_names = [
        'btn_start',
        'btn_stop',
        'btn_force_buy',
        'btn_force_sell',
        'btn_cancel_pending',
        'btn_risk_reset',
        'btn_balance_sync',
    ]
    converted: list[str] = []
    for name in button_names:
        old = f"getattr(self, '{name}', None)"
        new = f"safe_obj_getattr(self, '{name}', None)"
        if old in text:
            text = text.replace(old, new)
            converted.append(name)

    DASHBOARD.write_text(text, encoding='utf-8')
    remaining_balance = text.count("getattr(self, 'btn_balance_sync', None)")
    remaining_double = text.count('safe_obj_safe_obj_getattr')

    print('4B.4.3.6.6.11f hotfix applied')
    print(f" - dashboard.btn_balance_sync_getattr_replaced: {before}")
    print(f" - dashboard.defensive_button_getattr_converted: {','.join(converted) if converted else '-'}")
    print(f" - dashboard.double_safe_getattr_replaced: {double_before}")
    print(f" - dashboard.remaining_btn_balance_sync_getattr: {remaining_balance}")
    print(f" - dashboard.remaining_double_safe_getattr: {remaining_double}")
    if remaining_balance or remaining_double:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
