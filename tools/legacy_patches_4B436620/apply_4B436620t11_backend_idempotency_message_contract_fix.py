from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / 'tests' / 'test_dashboard_backend_idempotency.py'

REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Backend offline.", "Backend çevrimdışı"),
    ("Backend online, status payload alınamadı.", "Backend online, ancak /status okunamadı"),
)


def main() -> int:
    if not TEST_FILE.exists():
        raise RuntimeError(f'test file not found: {TEST_FILE}')

    original = TEST_FILE.read_text(encoding='utf-8')
    updated = original
    counts: dict[str, int] = {}
    for old, new in REPLACEMENTS:
        count = updated.count(old)
        counts[old] = count
        updated = updated.replace(old, new)

    TEST_FILE.write_text(updated, encoding='utf-8')

    py_compile.compile(str(TEST_FILE), doraise=True)

    final = TEST_FILE.read_text(encoding='utf-8')
    checks = {
        'offline_assert_updated': 'Backend çevrimdışı' in final,
        'status_degrade_assert_updated': 'Backend online, ancak /status okunamadı' in final,
        'old_offline_assert_absent': 'Backend offline.' not in final,
        'old_status_degrade_assert_absent': 'Backend online, status payload alınamadı.' not in final,
        'test_py_compile_ok': True,
    }

    print('4B.4.3.6.6.20t11 backend idempotency message contract fix applied')
    for old, count in counts.items():
        print(f' - replaced {old!r}: {count}')
    for key, value in checks.items():
        print(f' - {key}: {value}')

    if not all(checks.values()):
        raise RuntimeError(f'20t11 verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
