4B.4.3.6.6.29A-H1 Production Hardening Report Path Hygiene Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629A_H1_production_report_path_hygiene_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436629A_H1_production_report_path_hygiene.py

Check/test:
  $env:PYTHONPATH="src"
  python tools/check_4B436629A_H1_production_report_path_hygiene.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_production_report_path_hygiene_4B436629A_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
  $env:PYTHONPATH="src"
  python tools/run_4B436629A_H1_production_report_path_hygiene.py --reports-dir .\reports\production_hardening

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.29A-H1 production report path hygiene hotfix"
  git tag -a 4B.4.3.6.6.29A-H1 -m "Accepted production report path hygiene hotfix"
  git push
  git push origin 4B.4.3.6.6.29A-H1
