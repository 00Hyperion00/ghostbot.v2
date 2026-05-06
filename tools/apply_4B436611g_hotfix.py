from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()
DASHBOARD_PATH = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'


def main() -> None:
    if not DASHBOARD_PATH.exists():
        raise SystemExit(f'dashboard.py not found: {DASHBOARD_PATH}')

    text = DASHBOARD_PATH.read_text(encoding='utf-8')
    before = text

    # Normalize every accidental duplicated safe getter name, including repeated chains.
    # This is intentionally narrow: it does not rewrite arbitrary getattr calls anymore.
    replacements = 0
    while 'safe_obj_safe_obj_getattr' in text:
        count = text.count('safe_obj_safe_obj_getattr')
        replacements += count
        text = text.replace('safe_obj_safe_obj_getattr', 'safe_obj_getattr')

    # Defensive normalization for any longer accidental chain that may have been produced by earlier scripts.
    longer_patterns = [
        'safe_obj_safe_obj_safe_obj_getattr',
        'safe_obj_safe_obj_safe_obj_safe_obj_getattr',
    ]
    for pattern in longer_patterns:
        while pattern in text:
            count = text.count(pattern)
            replacements += count
            text = text.replace(pattern, 'safe_obj_getattr')

    remaining_double = text.count('safe_obj_safe_obj_getattr')
    if remaining_double:
        raise SystemExit(f'hotfix failed: remaining safe_obj_safe_obj_getattr={remaining_double}')

    if text != before:
        DASHBOARD_PATH.write_text(text, encoding='utf-8')

    print('4B.4.3.6.6.11g hotfix applied')
    print(f' - dashboard.safe_obj_safe_obj_getattr_replaced: {replacements}')
    print(f' - dashboard.remaining_double_safe_getattr: {remaining_double}')


if __name__ == '__main__':
    main()
