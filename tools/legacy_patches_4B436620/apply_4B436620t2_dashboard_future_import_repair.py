from __future__ import annotations

import py_compile
import re
from pathlib import Path

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAGMENT = Path(__file__).with_name('dashboard_20t2_final_contract_block.pyfrag')
BLOCK_RE = re.compile(
    r'\n?# BEGIN 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[A-Z0-9]*[^\n]*\n?',
    re.DOTALL,
)
START = '# BEGIN 4B.4.3.6.6.20T2 DASHBOARD FINAL CONTRACT RESTORE'


def _remove_misplaced_future_imports(text: str) -> tuple[str, int]:
    """Remove future-annotation imports that were appended mid-file by 20T.

    We keep a valid top-of-file future import if it already exists before real code.
    Any later `from __future__ import annotations` is illegal and must be removed.
    """
    lines = text.splitlines()
    result: list[str] = []
    removed = 0
    seen_real_code = False
    for line in lines:
        stripped = line.strip()
        if stripped == 'from __future__ import annotations':
            if seen_real_code:
                removed += 1
                continue
            result.append(line)
            continue
        if stripped and not stripped.startswith('#') and not (stripped.startswith('"""') or stripped.startswith("'''")):
            seen_real_code = True
        result.append(line)
    return '\n'.join(result) + ('\n' if text.endswith('\n') else ''), removed


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAGMENT.exists():
        raise RuntimeError(f'fragment not found: {FRAGMENT}')

    original = DASHBOARD.read_text(encoding='utf-8')
    without_blocks, removed_blocks = BLOCK_RE.subn('\n', original)
    without_bad_future, removed_future = _remove_misplaced_future_imports(without_blocks)

    fragment = FRAGMENT.read_text(encoding='utf-8')
    # Absolute guard: fragments appended to the end of a file must never contain future imports.
    fragment = '\n'.join(
        line for line in fragment.splitlines()
        if line.strip() != 'from __future__ import annotations'
    ).strip() + '\n'

    updated = without_bad_future.rstrip() + '\n\n' + fragment
    DASHBOARD.write_text(updated, encoding='utf-8')

    py_compile.compile(str(DASHBOARD), doraise=True)
    checks = {
        'removed_old_20_blocks': removed_blocks,
        'removed_misplaced_future_imports': removed_future,
        'final_block_present': START in updated,
        'midfile_future_import_absent': '\nfrom __future__ import annotations\n' not in updated.split(START, 1)[-1],
        'build_position_management_text': 'def build_position_management_text' in updated,
        'render_status_patch': '_render_status = _tb20t_render_status' in updated,
        'event_timeline_patch': '_render_event_timeline = _tb20t_render_event_timeline' in updated,
        'session_summary_patch': '_render_session_summary = _tb20t_render_session_summary' in updated,
        'audit_orders_format': 'Orders' in updated and 'corr=' in updated,
        'training_parser': '_tb20t_extract_training_output_path' in updated,
    }
    print('4B.4.3.6.6.20t2 dashboard future-import repair + final contract restore applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    required = {k: v for k, v in checks.items() if k != 'removed_old_20_blocks'}
    if not all(bool(v) for v in required.values()):
        raise RuntimeError(f'20t2 checks failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
