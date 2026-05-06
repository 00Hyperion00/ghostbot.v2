from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAG = ROOT / 'tools' / 'dashboard_20t3_last_five_contract_block.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T3 DASHBOARD LAST FIVE CONTRACT FIX'
END = '# END 4B.4.3.6.6.20T3 DASHBOARD LAST FIVE CONTRACT FIX'


def remove_existing_block(text: str) -> tuple[str, int]:
    pattern = re.compile(r'\n?# BEGIN 4B\.4\.3\.6\.6\.20T3 DASHBOARD LAST FIVE CONTRACT FIX.*?# END 4B\.4\.3\.6\.6\.20T3 DASHBOARD LAST FIVE CONTRACT FIX\n?', re.DOTALL)
    text, count = pattern.subn('\n', text)
    return text.rstrip() + '\n', count


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAG.exists():
        raise RuntimeError(f'fragment not found: {FRAG}')
    text = DASHBOARD.read_text(encoding='utf-8')
    text, removed = remove_existing_block(text)
    block = FRAG.read_text(encoding='utf-8').strip() + '\n'
    updated = text.rstrip() + '\n\n' + block
    DASHBOARD.write_text(updated, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)
    checks = {
        'old_t3_blocks_removed': removed,
        'hint_key': "'hint': hint" in updated,
        'pending_hint_uppercase': 'PENDING: giriş emri bekliyor' in updated,
        'api_post_widget_guard': 'tb20t3_button_disabled' in updated,
        'audit_orders_summary': 'Categories      :' in updated and 'Warnings/errors :' in updated,
        'render_logs_patch': 'obj._render_logs = _tb20t3_render_logs' in updated,
        'class_patch': '_TB20T3_PATCHED_CLASSES' in updated,
    }
    print('4B.4.3.6.6.20t3 dashboard last-five contract fix applied')
    for k, v in checks.items():
        print(f' - {k}: {v}')
    if not all(v is not False for v in checks.values()):
        raise RuntimeError(f'20t3 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
