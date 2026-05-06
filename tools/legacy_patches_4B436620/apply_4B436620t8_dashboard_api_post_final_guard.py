from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
FRAGMENT = ROOT / 'patches' / 'dashboard_20t8_api_post_final_guard.pyfrag'
START = '# BEGIN 4B.4.3.6.6.20T8 DASHBOARD API_POST FINAL GUARD'
END = '# END 4B.4.3.6.6.20T8 DASHBOARD API_POST FINAL GUARD'


def strip_block(text: str) -> tuple[str, int]:
    removed = 0
    while START in text and END in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before.rstrip() + '\n\n' + after.lstrip()
        removed += 1
    return text, removed


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    if not FRAGMENT.exists():
        raise RuntimeError(f'fragment not found: {FRAGMENT}')

    text = DASHBOARD.read_text(encoding='utf-8')
    text, removed = strip_block(text)
    fragment = FRAGMENT.read_text(encoding='utf-8').strip() + '\n'
    updated = text.rstrip() + '\n\n' + fragment
    DASHBOARD.write_text(updated, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)

    checks = {
        'old_t8_blocks_removed': removed,
        'getattribute_wrapper': 'def _tb20t8_dashboard_getattribute' in updated,
        'fail_closed_default': 'No explicit enabled evidence => fail closed' in updated,
        'operator_path_detection': 'def _tb20t8_action_from_path' in updated,
        'no_instance_api_post_delegate': "'api_post'" not in updated[updated.find(START):updated.find(END)],
        'class_patch': 'obj.__getattribute__ = _tb20t8_dashboard_getattribute' in updated,
    }
    print('4B.4.3.6.6.20t8 dashboard api-post final guard applied')
    for k, v in checks.items():
        print(f' - {k}: {v}')
    required = {k: v for k, v in checks.items() if k != 'old_t8_blocks_removed'}
    if not all(required.values()):
        raise RuntimeError(f'20t8 verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
