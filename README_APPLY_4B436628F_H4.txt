4B.4.3.6.6.28F-H4 Operator Cockpit Visualization Parity / Risk-Sizing Export Guard / Audit Source Label Cleanup

Apply:
  python tools/apply_4B436628F_H4_operator_cockpit_visualization_export_guard.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628F_H4_operator_cockpit_visualization_export_guard.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_operator_cockpit_visualization_export_guard_4B436628F_H4.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Restart cockpit:
  python tools/run_operator_cockpit_v2_desktop_4B436626D.py --allow-browser-fallback

Risk contract:
  No config mutation, no scheduler mutation, no training, no reload, no paper/live/order enablement.
