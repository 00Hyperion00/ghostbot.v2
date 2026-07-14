4B.4.3.6.6.61 Release Audit / Repository Hygiene / Pytest Collection Isolation

Purpose:
- Configure canonical pytest discovery from tests/ only.
- Exclude _patch_backup*, _patch_payload*, and legacy_patches from pytest collection.
- Prevent duplicate test module import mismatch with --import-mode=importlib.
- Report legacy API drift symbols without performing destructive cleanup.
- Preserve no paper submit / no network order / no live / no exchange-submit locks.

Apply:
  python tools/apply_4B436661_release_audit_pytest_collection_hygiene.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436661_release_audit_pytest_collection_hygiene.py --once-json

Run report:
  $env:PYTHONPATH="src"
  python tools/run_4B436661_release_audit_pytest_collection_hygiene.py --reports-dir .\reports\recovery --once-json

Tests:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_release_audit_pytest_collection_hygiene_4B436661.py
  python -m pytest -q
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Safety:
- No runtime start.
- No health probe.
- No metrics collection.
- No paper submit.
- No network order.
- No private API access.
- No live-real approval.
- No exchange submit.
