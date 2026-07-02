4B.4.3.6.6.33D Runtime Safety Lockdown

Apply:
  python tools/apply_4B436633D_runtime_safety_lockdown.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436633D_runtime_safety_lockdown.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_runtime_safety_lockdown_4B436633D.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436633D_runtime_safety_lockdown.py --reports-dir .\reports\recovery --once-json

This patch is read-only from a trading perspective. It does not submit orders, train, reload, activate overlay, or clean files.
