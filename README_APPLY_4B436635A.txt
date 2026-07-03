4B.4.3.6.6.35A — Post-Governance Runtime Readiness Planning

Apply:
  python tools/apply_4B436635A_post_governance_runtime_readiness_planning.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436635A_post_governance_runtime_readiness_planning.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_post_governance_runtime_readiness_planning_4B436635A.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436635A_post_governance_runtime_readiness_planning.py --reports-dir .\reports\recovery --once-json

Safety:
  Planning only. No exchange submit, no paper transition, no live-real approval, no runtime overlay, no archive/delete/move/dedup action.
