from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / 'src' / 'tradebot' / 'engine.py'

SAFE_LATEST_MARK_PRICE = '''    def _latest_mark_price(self) -> float | None:
        """Return the latest known mark price without assuming runtime-only attributes exist.

        Some unit tests build TradeBotEngine via object.__new__ and only attach the
        attributes needed by the target scenario. Restart recovery can call this
        helper before websocket/book state is attached, so this method must be
        attribute-safe.
        """
        latest_book = getattr(self, '_latest_book', None)
        if isinstance(latest_book, dict):
            for key in ('bestBid', 'bestAsk'):
                value = latest_book.get(key)
                if value not in (None, '', 0, 0.0):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue

        closed_candles = getattr(self, '_closed_candles', None) or []
        if closed_candles:
            try:
                value = getattr(closed_candles[-1], 'close', None)
                if value not in (None, ''):
                    return float(value)
            except (TypeError, ValueError, AttributeError, IndexError):
                return None
        return None
'''


def replace_latest_mark_price(source: str) -> tuple[str, int]:
    pattern = re.compile(
        r"    def _latest_mark_price\(self\) -> float \| None:\n.*?(?=\n    def _latest_atr\(self\))",
        re.DOTALL,
    )
    new_source, count = pattern.subn(SAFE_LATEST_MARK_PRICE.rstrip(), source, count=1)
    return new_source, count


def main() -> None:
    if not ENGINE_PATH.exists():
        raise SystemExit(f'engine.py not found: {ENGINE_PATH}')

    source = ENGINE_PATH.read_text(encoding='utf-8')
    updated, replaced = replace_latest_mark_price(source)
    if replaced != 1:
        raise SystemExit(f'latest_mark_price method replacement failed; replaced={replaced}')

    # Syntax gate before writing.
    ast.parse(updated)
    ENGINE_PATH.write_text(updated, encoding='utf-8')

    after = ENGINE_PATH.read_text(encoding='utf-8')
    method_start = after.find('    def _latest_mark_price')
    method_end = after.find('\n    def _latest_atr', method_start)
    method = after[method_start:method_end]

    checks = {
        'latest_mark_price_safe_latest_book': "getattr(self, '_latest_book', None)" in method,
        'latest_mark_price_safe_closed_candles': "getattr(self, '_closed_candles', None)" in method,
        'latest_mark_price_no_raw_latest_book': 'self._latest_book' not in method,
        'latest_mark_price_no_raw_closed_candles': 'self._closed_candles' not in method,
    }
    if not all(checks.values()):
        raise SystemExit(f'4B.4.3.6.6.12b verification failed: {checks}')

    print('4B.4.3.6.6.12b latest mark price compatibility hotfix applied')
    print(f' - engine: {checks}')


if __name__ == '__main__':
    main()
