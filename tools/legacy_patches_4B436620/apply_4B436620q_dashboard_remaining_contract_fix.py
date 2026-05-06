from __future__ import annotations

import re
from pathlib import Path

START = '# BEGIN 4B.4.3.6.6.20Q DASHBOARD REMAINING CONTRACT FIX'
END = '# END 4B.4.3.6.6.20Q DASHBOARD REMAINING CONTRACT FIX'
ROOT = Path.cwd()
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
BLOCK_PATH = Path(__file__).resolve().with_name('dashboard_20q_block.py.txt')
OLD_BLOCK_RE = re.compile(
    r"\n?# BEGIN 4B\.4\.3\.6\.6\.20[A-Z0-9]+[^\n]*\n.*?# END 4B\.4\.3\.6\.6\.20[A-Z0-9]+[^\n]*\n?",
    re.DOTALL,
)


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    block = BLOCK_PATH.read_text(encoding='utf-8').strip() + '\n'
    text = DASHBOARD.read_text(encoding='utf-8')
    stripped, removed = OLD_BLOCK_RE.subn('\n', text)
    if START in stripped and END in stripped:
        stripped = stripped.split(START, 1)[0].rstrip() + '\n'
    updated = stripped.rstrip() + '\n\n' + block
    DASHBOARD.write_text(updated, encoding='utf-8')
    checks = {
        'old_blocks_removed': removed >= 0,
        'position_is_dust_key': "'position_is_dust'" in updated,
        'health_reason_prefixed': 'HEALTH_ANOMALY:' in updated,
        'safe_mode_hint_spaced': 'safe mode aktif' in updated,
        'force_sell_hint_turkish': 'force sell aktif' in updated,
        'event_box_render': "'event-box'" in updated,
        'audit_filter_dict': 'def filter_audit_events(events, filters=None' in updated,
        'status_online_degrade': 'Backend online, ancak /status okunamadı' in updated,
        'offline_exact': 'Backend çevrimdışı ({reason}).' in updated,
        'class_auto_patch': '_q_patch_dashboard_classes()' in updated,
    }
    print('4B.4.3.6.6.20q dashboard remaining contract fix applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise RuntimeError(f'20Q verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
