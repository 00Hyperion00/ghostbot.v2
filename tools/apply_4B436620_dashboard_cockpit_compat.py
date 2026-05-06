from __future__ import annotations

from pathlib import Path

OLD = "assert status['contract_version'] == '4B.4.3.6.6.19'"
NEW = "assert status['contract_version'] == '4B.4.3.6.6.20'"
FILES = [
    Path('tests/test_runtime_observability_event_audit.py'),
    Path('tests/test_config_profile_safety.py'),
    Path('tests/test_operator_diagnostics.py'),
    Path('tests/test_strategy_decision_audit.py'),
]


def patch_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {'exists': False, 'replacements': 0, 'remaining_old_status_assert': False, 'new_status_assert_present': False}
    text = path.read_text(encoding='utf-8')
    replacements = text.count(OLD)
    text = text.replace(OLD, NEW)
    path.write_text(text, encoding='utf-8')
    return {
        'exists': True,
        'replacements': replacements,
        'remaining_old_status_assert': OLD in text,
        'new_status_assert_present': NEW in text,
    }


def main() -> int:
    results = {str(path): patch_file(path) for path in FILES}
    print('4B.4.3.6.6.20 dashboard cockpit compatibility patch applied')
    for path, result in results.items():
        print(f' - {path}: {result}')
    bad = [path for path, result in results.items() if result.get('exists') and result.get('remaining_old_status_assert')]
    if bad:
        print(f'ERROR: old status contract assertions remain: {bad}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
