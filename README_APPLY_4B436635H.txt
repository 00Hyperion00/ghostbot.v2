4B.4.3.6.6.35H Runtime Readiness Planning Closure

Scope:
- 35A-35G local tag audit
- Planning evidence acceptance ledger
- No-submit Phase-35 interim seal

This patch is planning/governance only. It does not execute collection, probe, paper, live, exchange submit, runtime overlay, training/reload, archive, delete, move, or deduplication actions.

Apply:
  python tools/apply_4B436635H_runtime_readiness_planning_closure.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436635H_runtime_readiness_planning_closure.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_runtime_readiness_planning_closure_4B436635H.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436635H_runtime_readiness_planning_closure.py --reports-dir .\reports\recovery --once-json

Expected decision:
  RUNTIME_READINESS_PLANNING_CLOSURE_READY_NO_SUBMIT_PHASE_35_INTERIM_SEALED
