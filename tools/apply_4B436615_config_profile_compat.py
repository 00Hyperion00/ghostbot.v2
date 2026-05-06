from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'tests' / 'test_runtime_observability_event_audit.py'


def main() -> int:
    result: dict[str, object] = {'exists': TARGET.exists()}
    if TARGET.exists():
        text = TARGET.read_text(encoding='utf-8')
        before = text
        text = text.replace("assert status['contract_version'] == '4B.4.3.6.6.14'", "assert status['contract_version'] == '4B.4.3.6.6.15'")
        text = text.replace('assert status["contract_version"] == "4B.4.3.6.6.14"', 'assert status["contract_version"] == "4B.4.3.6.6.15"')
        TARGET.write_text(text, encoding='utf-8')
        result['replacements'] = before.count('4B.4.3.6.6.14') - text.count('4B.4.3.6.6.14')
        result['remaining_old_status_assert'] = "status['contract_version'] == '4B.4.3.6.6.14'" in text or 'status["contract_version"] == "4B.4.3.6.6.14"' in text
        result['new_status_assert_present'] = "status['contract_version'] == '4B.4.3.6.6.15'" in text or 'status["contract_version"] == "4B.4.3.6.6.15"' in text
        if result['remaining_old_status_assert']:
            raise RuntimeError('Old 4B.4.3.6.6.14 status contract assertion still exists')
    print('4B.4.3.6.6.15 config/profile compatibility patch applied')
    for key, value in result.items():
        print(f' - runtime_observability_test.{key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
