4B.4.3.6.6.29E Production Readiness Consolidation Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629E_production_readiness_consolidation_gate_evidence_merge_paper_preflight_live_real_hard_block_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436629E_production_readiness_consolidation_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436629E_production_readiness_consolidation_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_production_readiness_consolidation_gate_4B436629E.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence report:
  $env:PYTHONPATH="src"
  python tools/run_4B436629E_production_readiness_consolidation_gate.py --reports-dir .\reports\production_hardening

Expected decision:
  PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED
