from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAG = ROOT / 'tools' / 'dashboard_20t7_final_two_exact_contract_block.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T7 DASHBOARD FINAL TWO EXACT CONTRACT FIX'
END = '# END 4B.4.3.6.6.20T7 DASHBOARD FINAL TWO EXACT CONTRACT FIX'


def strip_block(text: str, start: str, end: str) -> tuple[str, int]:
    pattern = re.compile(re.escape(start) + r'.*?' + re.escape(end) + r'\n?', re.DOTALL)
    return pattern.subn('', text)


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAG.exists():
        raise RuntimeError(f'fragment not found: {FRAG}')

    text = DASHBOARD.read_text(encoding='utf-8')
    block = FRAG.read_text(encoding='utf-8').strip() + '\n'
    text, removed = strip_block(text, START, END)
    text = text.rstrip() + '\n\n' + block
    DASHBOARD.write_text(text, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)

    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'old_t7_blocks_removed': removed,
        'api_post_instance_sentinel': 'has_instance_http_sentinel' in final,
        'api_post_no_instance_delegate': 'Do not call instance api_post' in final,
        'severity_no_double_count': 'has_severity_counts' in final,
        'auto_info_as_warning': "raw_s == 'info'" in final,
        'audit_summary_override': "globals()['build_audit_summary_text'] = build_audit_summary_text" in final,
        'render_logs_patch': "setattr(_tb20t7_obj, '_render_logs', _tb20t7_render_logs)" in final,
        'class_patch': "setattr(_tb20t7_obj, '_api_post', _tb20t7_api_post)" in final,
    }
    print('4B.4.3.6.6.20t7 dashboard final two exact contract fix applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    required = {k: v for k, v in checks.items() if k != 'old_t7_blocks_removed'}
    if not all(required.values()):
        raise RuntimeError(f'20t7 verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
