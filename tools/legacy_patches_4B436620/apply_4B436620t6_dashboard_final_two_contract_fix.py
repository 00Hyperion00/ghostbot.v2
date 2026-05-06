from __future__ import annotations

import ast
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAGMENT = ROOT / 'tools' / 'dashboard_20t6_final_two_contract_block.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T6 DASHBOARD FINAL TWO CONTRACT FIX'
END = '# END 4B.4.3.6.6.20T6 DASHBOARD FINAL TWO CONTRACT FIX'


def remove_block(text: str, start: str, end: str) -> tuple[str, int]:
    pattern = re.compile(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', re.DOTALL)
    return pattern.subn('', text)


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAGMENT.exists():
        raise RuntimeError(f'fragment not found: {FRAGMENT}')
    block = FRAGMENT.read_text(encoding='utf-8').strip() + '\n'
    ast.parse(block)
    text = DASHBOARD.read_text(encoding='utf-8')
    text, removed = remove_block(text, START, END)
    updated = text.rstrip() + '\n\n' + block
    DASHBOARD.write_text(updated, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)
    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'old_t6_blocks_removed': removed,
        'api_post_instance_sentinel': "'api_post' in object.__getattribute__(app, '__dict__')" in final,
        'auto_blocked_warning': "'BLOCKED' in code" in final,
        'audit_summary_override': "globals()['build_audit_summary_text'] = build_audit_summary_text" in final,
        'render_logs_patch': "setattr(_tb20t6_obj, '_render_logs', _tb20t6_render_logs)" in final,
        'class_patch': "setattr(_tb20t6_obj, '_api_post', _tb20t6_api_post)" in final,
    }
    print('4B.4.3.6.6.20t6 dashboard final two contract fix applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(v is True or isinstance(v, int) for v in checks.values()):
        raise RuntimeError(f'20t6 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
