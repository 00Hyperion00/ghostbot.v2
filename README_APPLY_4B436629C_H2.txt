4B.4.3.6.6.29C-H2 SQLite probe explicit connection close hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629C_H2_sqlite_probe_explicit_connection_close_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436629C_H2_sqlite_probe_explicit_connection_close.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436629C_H2_sqlite_probe_explicit_connection_close.py --once-json
  python tools/check_4B436629C_H1_sqlite_probe_windows_handle_cleanup.py --once-json
  python tools/check_4B436629C_sqlite_audit_ledger_upgrade.py --once-json

  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_sqlite_audit_ledger_upgrade_4B436629C.py tests/test_sqlite_probe_windows_handle_cleanup_4B436629C_H1.py tests/test_sqlite_probe_explicit_connection_close_4B436629C_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Reports:
  $env:PYTHONPATH="src"
  python tools/run_4B436629C_sqlite_audit_ledger_upgrade.py --reports-dir .\reports\production_hardening
  python tools/run_4B436629C_H2_sqlite_probe_explicit_connection_close.py --reports-dir .\reports\production_hardening

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.29C-H2 SQLite probe explicit connection close hotfix"
  git tag -a 4B.4.3.6.6.29C-H2 -m "Accepted SQLite probe explicit connection close hotfix"
  git push
  git push origin 4B.4.3.6.6.29C-H2
