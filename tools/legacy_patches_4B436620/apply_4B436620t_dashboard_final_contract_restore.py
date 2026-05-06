from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAGMENT = Path(__file__).with_name('dashboard_20t_final_contract_block.pyfrag')
START_RE = re.compile(r'\n?# BEGIN 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*\n?', re.DOTALL)
START = '# BEGIN 4B.4.3.6.6.20T DASHBOARD FINAL CONTRACT RESTORE'


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAGMENT.exists():
        raise RuntimeError(f'fragment not found: {FRAGMENT}')

    original = DASHBOARD.read_text(encoding='utf-8')
    cleaned, removed = START_RE.subn('\n', original)
    fragment = FRAGMENT.read_text(encoding='utf-8').strip() + '\n'
    updated = cleaned.rstrip() + '\n\n' + fragment
    DASHBOARD.write_text(updated, encoding='utf-8')

    py_compile.compile(str(DASHBOARD), doraise=True)
    checks = {
        'removed_old_20_blocks': removed,
        'final_block_present': START in updated,
        'build_position_management_text': 'def build_position_management_text' in updated,
        'render_status_patch': '_render_status = _tb20t_render_status' in updated,
        'event_timeline_patch': '_render_event_timeline = _tb20t_render_event_timeline' in updated,
        'session_summary_patch': '_render_session_summary = _tb20t_render_session_summary' in updated,
        'audit_orders_format': 'Orders' in updated and 'corr=' in updated,
        'training_parser': '_tb20t_extract_training_output_path' in updated,
    }
    print('4B.4.3.6.6.20t dashboard final contract restore applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(bool(v) for v in checks.values() if key != 'removed_old_20_blocks'):
        raise RuntimeError(f'20t checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
