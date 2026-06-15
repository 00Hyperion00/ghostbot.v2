4B.4.3.6.6.28F-H2 Operator Cockpit HYP-006 Export Source Parity / Safe Operator Actions Ledger Binding Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436628F_H2_operator_cockpit_hyp006_export_source_parity_safe_operator_actions_ledger_binding_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436628F_H2_operator_cockpit_export_parity.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436628F_H2_operator_cockpit_export_parity.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_operator_cockpit_export_parity_4B436628F_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Restart cockpit:
  python tools/run_operator_cockpit_v2_desktop_4B436626D.py --allow-browser-fallback

Expected:
  safe_operator_actions.exports source fields must point to reports\hyp006_r1_canonical, not reports\hyp005_r1_canonical.
  latest-ledger export must download HYP-006 JSONL ledger.

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.28F-H2 Operator Cockpit HYP-006 export parity"
  git tag -a 4B.4.3.6.6.28F-H2 -m "Accepted Operator Cockpit HYP-006 export source parity baseline"
  git push
  git push origin 4B.4.3.6.6.28F-H2
