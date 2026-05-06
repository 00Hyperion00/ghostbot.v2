from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import run_4B436621_acceptance_tests as runner


def test_group_registry_contains_release_gate_groups() -> None:
    expected = {
        'compileall',
        'dashboard_acceptance',
        'dashboard_full_gate',
        'lifecycle_risk',
        'ai_model',
        'feature_schema',
        'training_pipeline',
        'api',
    }
    assert expected.issubset(set(runner.TEST_GROUPS))


def test_missing_paths_fail_closed(tmp_path: Path) -> None:
    group = runner.TestGroup(
        name='missing_demo',
        description='missing path demo',
        command=('-c', 'print("should not run")'),
        required_paths=('does_not_exist.py',),
    )
    result = runner.run_group(tmp_path, group, timestamp='unit', allow_missing=False)
    assert result.status == 'MISSING'
    assert result.returncode == 127
    assert result.missing_paths == ['does_not_exist.py']


def test_run_group_pass_and_report_generation(tmp_path: Path) -> None:
    group = runner.TestGroup(
        name='smoke',
        description='unit smoke',
        command=('-c', 'print("ok")'),
        required_paths=(),
    )
    result = runner.run_group(tmp_path, group, timestamp='unit')
    assert result.status == 'PASS'
    assert 'ok' in result.stdout_tail

    json_path, md_path = runner.write_reports(tmp_path, [result], timestamp='unit', prefix='acceptance_unit')
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert payload['decision'] == 'PASS'
    assert payload['summary']['PASS'] == 1
    assert 'Decision: **PASS**' in md_path.read_text(encoding='utf-8')


def test_resolve_groups_rejects_unknown_group() -> None:
    try:
        runner.resolve_groups(['unknown_group'], None)
    except SystemExit as exc:
        assert 'Unknown acceptance group' in str(exc)
    else:
        raise AssertionError('unknown group must fail closed')
