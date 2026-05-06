from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = '4B.4.3.6.6.16'
OLD_CONTRACTS = ['4B.4.3.6.6.15', '4B.4.3.6.6.14', '4B.4.3.6.6.13']


def patch_runtime_observability_test() -> dict[str, object]:
    path = PROJECT_ROOT / 'tests' / 'test_runtime_observability_event_audit.py'
    if not path.exists():
        return {'exists': False, 'replacements': 0, 'remaining_old_status_assert': False, 'new_status_assert_present': False}
    text = path.read_text(encoding='utf-8')
    before = text
    for old in OLD_CONTRACTS:
        text = text.replace(f"assert status['contract_version'] == '{old}'", f"assert status['contract_version'] == '{CONTRACT}'")
        text = text.replace(f'assert status["contract_version"] == "{old}"', f'assert status["contract_version"] == "{CONTRACT}"')
    replacements = 0 if text == before else 1
    path.write_text(text, encoding='utf-8')
    remaining_old = any(
        f"assert status['contract_version'] == '{old}'" in text or f'assert status["contract_version"] == "{old}"' in text
        for old in OLD_CONTRACTS
    )
    new_present = f"assert status['contract_version'] == '{CONTRACT}'" in text or f'assert status["contract_version"] == "{CONTRACT}"' in text
    return {'exists': True, 'replacements': replacements, 'remaining_old_status_assert': remaining_old, 'new_status_assert_present': new_present}


def main() -> int:
    result = patch_runtime_observability_test()
    print('4B.4.3.6.6.16 launcher compatibility patch applied')
    print(f' - runtime_observability_test.exists: {result["exists"]}')
    print(f' - runtime_observability_test.replacements: {result["replacements"]}')
    print(f' - runtime_observability_test.remaining_old_status_assert: {result["remaining_old_status_assert"]}')
    print(f' - runtime_observability_test.new_status_assert_present: {result["new_status_assert_present"]}')
    return 1 if result['remaining_old_status_assert'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
