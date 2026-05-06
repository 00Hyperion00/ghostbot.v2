from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path.cwd()
RUNNER = ROOT / 'tools' / 'run_4B436621_acceptance_tests.py'
SELF_TEST = ROOT / 'tests' / 'test_acceptance_runner_4B436621.py'
REPORTS = ROOT / 'reports'


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    checks = {
        'runner_exists': RUNNER.exists(),
        'self_test_exists': SELF_TEST.exists(),
        'reports_dir_exists': REPORTS.exists(),
    }
    if checks['runner_exists']:
        py_compile.compile(str(RUNNER), doraise=True)
        checks['runner_py_compile_ok'] = True
    else:
        checks['runner_py_compile_ok'] = False
    if checks['self_test_exists']:
        py_compile.compile(str(SELF_TEST), doraise=True)
        checks['self_test_py_compile_ok'] = True
    else:
        checks['self_test_py_compile_ok'] = False

    print('4B.4.3.6.6.21a acceptance test runner tooling applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise RuntimeError(f'21a apply verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
