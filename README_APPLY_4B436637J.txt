4B.4.3.6.6.37J Report Commit Policy

Scope:
- canonical evidence selection
- commit whitelist
- report provenance guard
- no-submit P0-9 hardening gate

No actions performed:
- no git add/commit/tag/push
- no report delete/move/dedup/archive
- no paper/live/exchange submit
- no network/http/signed request
- no runtime overlay/reload/training

Apply:
  python tools/apply_4B436637J_report_commit_policy.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436637J_report_commit_policy.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_report_commit_policy_4B436637J.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436637J_report_commit_policy.py --reports-dir .eportsecovery --once-json
