from __future__ import annotations

from pathlib import Path
import ast
import py_compile

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAG = ROOT / 'tools' / 'dashboard_20t5_final_three_contract_block.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T5 DASHBOARD FINAL THREE CONTRACT FIX'
END = '# END 4B.4.3.6.6.20T5 DASHBOARD FINAL THREE CONTRACT FIX'


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
        'old_t5_blocks_removed': removed,
        'api_post_safe_override': '_tb20t5_api_post' in updated and '_last_status' in updated and 'build_operator_control_state' in updated,
        'audit_recursive_counts': '_tb20t5_extract_count_maps' in updated and "category_counts['Orders'] = 1" in updated,
        'warnings_errors_line': 'Warnings/errors : {warning_count} / {error_count}' in updated,
        'safe_render_logs_attrs': '_tb20t5_safe_getattr(self, attr, [])' in updated,
        'class_patch': "setattr(_tb20t5_obj, '_api_post'" in updated and "setattr(_tb20t5_obj, '_render_logs'" in updated,
    }
    print('4B.4.3.6.6.20t5 dashboard final three contract fix applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(bool(value) for key, value in checks.items() if key != 'old_t5_blocks_removed'):
        raise RuntimeError(f'20t5 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
