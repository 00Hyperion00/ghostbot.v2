4B.4.3.6.6.28F-H3 Operator Cockpit HYP-006 UI Label Parity / Native Desktop Export Bridge 412 Handling Hotfix

Apply:
  python tools/apply_4B436628F_H3_operator_cockpit_ui_export_bridge_hotfix.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628F_H3_operator_cockpit_ui_export_bridge_hotfix.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_operator_cockpit_ui_export_bridge_4B436628F_H3.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Restart cockpit:
  python tools/run_operator_cockpit_v2_desktop_4B436626D.py --allow-browser-fallback

Expected UI:
  HYP-006-R1 Shadow Sample Expansion
  28F-H3 · READ ONLY
  28F-H3 · HYP006 EXPORTS

Risk contract:
  No config mutation.
  No scheduler mutation.
  No training/reload.
  No paper/live/order enablement.
