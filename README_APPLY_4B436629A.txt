4B.4.3.6.6.29A Production Hardening P0

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629A_production_hardening_p0_repo_hygiene_install_contract_strict_config_api_auth_sqlite_audit_promotion_gate_isolation_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436629A_production_hardening_p0.py

Check/test:
  $env:PYTHONPATH="src"
  python tools/check_4B436629A_production_hardening_p0.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_production_hardening_p0_4B436629A.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run decision report:
  python tools/run_4B436629A_production_hardening_p0.py --reports-dir .\reports\production_hardening

Expected safety state:
  approved_for_live_real=False
  approved_for_paper_candidate=False
  approved_for_runtime_overlay_activation_candidate=False
  training_performed=False
  reload_performed=False
  trading_action_performed=False
