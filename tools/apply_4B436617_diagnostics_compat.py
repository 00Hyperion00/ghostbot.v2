from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_FILES = [
    ROOT / 'tests' / 'test_runtime_observability_event_audit.py',
    ROOT / 'tests' / 'test_config_profile_safety.py',
]
OLD = "status['contract_version'] == '4B.4.3.6.6.16'"
NEW = "status['contract_version'] == '4B.4.3.6.6.17'"
OLD_DQ = 'status["contract_version"] == "4B.4.3.6.6.16"'
NEW_DQ = 'status["contract_version"] == "4B.4.3.6.6.17"'


def patch_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {'exists': False, 'replacements': 0, 'remaining_old_status_assert': False, 'new_status_assert_present': False}
    text = path.read_text(encoding='utf-8')
    before = text
    text = text.replace(OLD, NEW).replace(OLD_DQ, NEW_DQ)
    path.write_text(text, encoding='utf-8')
    return {
        'exists': True,
        'replacements': before.count(OLD) + before.count(OLD_DQ),
        'remaining_old_status_assert': OLD in text or OLD_DQ in text,
        'new_status_assert_present': NEW in text or NEW_DQ in text,
    }


def main() -> int:
    results = {str(path.relative_to(ROOT)): patch_file(path) for path in TEST_FILES}
    print('4B.4.3.6.6.17 diagnostics compatibility patch applied')
    for name, result in results.items():
        print(f' - {name}: {result}')
    if any(result.get('remaining_old_status_assert') for result in results.values()):
        raise SystemExit(1)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
