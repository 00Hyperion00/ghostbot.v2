4B.4.3.6.6.30A-H1 Paper Preflight Config Fields Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630A_H1_paper_preflight_config_fields_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630A_H1_paper_preflight_config_fields.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630A_H1_paper_preflight_config_fields.py --once-json
  python tools/check_4B436630A_paper_candidate_preflight.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_candidate_preflight_4B436630A.py tests/test_paper_preflight_config_fields_4B436630A_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630A_paper_candidate_preflight.py --reports-dir .\reports\production_hardening
  python tools/run_4B436630A_H1_paper_preflight_config_fields.py --reports-dir .\reports\production_hardening

Expected:
  PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED
  PAPER_PREFLIGHT_CONFIG_FIELDS_READY_LIVE_REAL_BLOCKED

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30A-H1 paper preflight config fields hotfix"
  git tag -a 4B.4.3.6.6.30A-H1 -m "Accepted paper preflight config fields hotfix"
  git push
  git push origin 4B.4.3.6.6.30A-H1
