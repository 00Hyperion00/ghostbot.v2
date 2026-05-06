from __future__ import annotations

from pathlib import Path
import ast
import py_compile

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAG = ROOT / 'tools' / 'dashboard_20t4_last_three_contract_block.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T4 DASHBOARD LAST THREE CONTRACT FIX'
END = '# END 4B.4.3.6.6.20T4 DASHBOARD LAST THREE CONTRACT FIX'


def remove_block(text: str, start: str, end: str) -> tuple[str, int]:
    count = 0
    while start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before.rstrip() + '\n\n' + after.lstrip()
        count += 1
    return text, count


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAG.exists():
        raise RuntimeError(f'fragment not found: {FRAG}')
    frag = FRAG.read_text(encoding='utf-8')
    ast.parse(frag)
    text = DASHBOARD.read_text(encoding='utf-8')
    text, removed = remove_block(text, START, END)
    updated = text.rstrip() + '\n\n' + frag.strip() + '\n'
    DASHBOARD.write_text(updated, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)
    checks = {
        'old_t4_blocks_removed': removed,
        'api_post_override': '_tb20t4_api_post' in updated and "setattr(_tb20t4_obj, '_api_post'" in updated,
        'audit_summary_override': "globals()['build_audit_summary_text'] = build_audit_summary_text" in updated,
        'warnings_errors_line': 'Warnings/errors : {warning_count} / {error_count}' in updated,
        'orders_category_support': "return 'Orders'" in updated,
        'render_logs_patch': '_tb20t4_render_logs' in updated,
        'class_patch': "setattr(_tb20t4_obj, '_render_logs'" in updated,
    }
    print('4B.4.3.6.6.20t4 dashboard last-three contract fix applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(bool(v) for v in checks.values() if not isinstance(v, int)):
        raise RuntimeError(f'20t4 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
