4B.4.3.6.6.29D Replay / Backtest / Walk-forward Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629D_replay_backtest_walkforward_gate_deterministic_replay_model_hash_lkg_oos_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436629D_replay_backtest_walkforward_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436629D_replay_backtest_walkforward_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_replay_backtest_walkforward_gate_4B436629D.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Report:
  $env:PYTHONPATH="src"
  python tools/run_4B436629D_replay_backtest_walkforward_gate.py --reports-dir .\reports\production_hardening

Expected decision:
  REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED
