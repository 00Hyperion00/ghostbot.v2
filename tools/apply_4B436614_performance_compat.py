from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / 'tests' / 'test_runtime_observability_event_audit.py'
OLD = "assert status['contract_version'] == '4B.4.3.6.6.13'"
NEW = "assert status['contract_version'] == '4B.4.3.6.6.14'"


def main() -> int:
    if not TEST_PATH.exists():
        print('4B.4.3.6.6.14 performance compat hotfix skipped: runtime observability test not found')
        return 0
    text = TEST_PATH.read_text(encoding='utf-8')
    replacements = text.count(OLD)
    if replacements:
        text = text.replace(OLD, NEW)
        TEST_PATH.write_text(text, encoding='utf-8')
    updated = TEST_PATH.read_text(encoding='utf-8')
    remaining = updated.count(OLD)
    present = NEW in updated
    print('4B.4.3.6.6.14 performance analytics compatibility hotfix applied')
    print(f' - runtime_observability_test.exists: {TEST_PATH.exists()}')
    print(f' - runtime_observability_test.replacements: {replacements}')
    print(f' - runtime_observability_test.remaining_old_status_assert: {remaining}')
    print(f' - runtime_observability_test.new_status_assert_present: {present}')
    if remaining:
        raise RuntimeError('Old 4B.4.3.6.6.13 status contract assertion still exists in runtime observability test')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
