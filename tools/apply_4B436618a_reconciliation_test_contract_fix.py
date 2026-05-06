from __future__ import annotations

from pathlib import Path
import ast

OLD_SINGLE = "assert status['contract_version'] == '4B.4.3.6.6.17'"
NEW_SINGLE = "assert status['contract_version'] == '4B.4.3.6.6.18'"
OLD_DOUBLE = 'assert status["contract_version"] == "4B.4.3.6.6.17"'
NEW_DOUBLE = 'assert status["contract_version"] == "4B.4.3.6.6.18"'


def main() -> int:
    root = Path.cwd()
    test_path = root / 'tests' / 'test_runtime_observability_event_audit.py'
    if not test_path.exists():
        raise SystemExit(f'Missing file: {test_path}')

    text = test_path.read_text(encoding='utf-8')
    before = text
    replacements = 0

    old_single_count = text.count(OLD_SINGLE)
    if old_single_count:
        text = text.replace(OLD_SINGLE, NEW_SINGLE)
        replacements += old_single_count

    old_double_count = text.count(OLD_DOUBLE)
    if old_double_count:
        text = text.replace(OLD_DOUBLE, NEW_DOUBLE)
        replacements += old_double_count

    if text != before:
        ast.parse(text)
        test_path.write_text(text, encoding='utf-8')
    else:
        ast.parse(text)

    updated = test_path.read_text(encoding='utf-8')
    remaining_old_single = OLD_SINGLE in updated
    remaining_old_double = OLD_DOUBLE in updated
    new_present = NEW_SINGLE in updated or NEW_DOUBLE in updated

    report = {
        'exists': True,
        'replacements': replacements,
        'remaining_old_status_assert': bool(remaining_old_single or remaining_old_double),
        'new_status_assert_present': bool(new_present),
    }

    if report['remaining_old_status_assert'] or not report['new_status_assert_present']:
        raise SystemExit(f'4B.4.3.6.6.18a contract fix failed: {report}')

    print('4B.4.3.6.6.18a reconciliation test contract hotfix applied')
    print(f" - test_runtime_observability_event_audit: {report}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
