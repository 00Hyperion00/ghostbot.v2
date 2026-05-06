from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / 'tests' / 'test_runtime_observability_event_audit.py',
    ROOT / 'tests' / 'test_config_profile_safety.py',
    ROOT / 'tests' / 'test_operator_diagnostics.py',
]
OLD = "status['contract_version'] == '4B.4.3.6.6.18'"
NEW = "status['contract_version'] == '4B.4.3.6.6.19'"


def patch_file(path: Path) -> dict[str, object]:
    result = {'exists': path.exists(), 'replacements': 0, 'remaining_old_status_assert': False, 'new_status_assert_present': False}
    if not path.exists():
        return result
    text = path.read_text(encoding='utf-8')
    count = text.count(OLD)
    if count:
        text = text.replace(OLD, NEW)
        path.write_text(text, encoding='utf-8')
    result['replacements'] = count
    result['remaining_old_status_assert'] = OLD in text
    result['new_status_assert_present'] = NEW in text
    return result


def main() -> int:
    results = {str(path.relative_to(ROOT)): patch_file(path) for path in TARGETS}
    print('4B.4.3.6.6.19 decision audit compatibility patch applied')
    for path, info in results.items():
        print(f' - {path}: {info}')
    failed = [path for path, info in results.items() if info.get('exists') and info.get('remaining_old_status_assert')]
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
