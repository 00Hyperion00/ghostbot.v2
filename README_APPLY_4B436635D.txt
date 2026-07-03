4B.4.3.6.6.35D Collection Preflight Gate

Apply:
  python tools/apply_4B436635D_collection_preflight_gate.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436635D_collection_preflight_gate.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_collection_preflight_gate_4B436635D.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436635D_collection_preflight_gate.py --reports-dir .eportsecovery --once-json

Safety:
  This patch is planning/preflight only. It does not start runtime evidence collection,
  public market data collection, runtime probes, private API reads, paper transition,
  live trading, order submit, runtime overlay, training, reload, archive execution,
  destructive cleanup, or next-phase unlock.
