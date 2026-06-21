4B.4.3.6.6.30S Paper Mode Runtime Guardrail

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630S_paper_mode_runtime_guardrail_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630S_paper_mode_runtime_guardrail.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630S_paper_mode_runtime_guardrail.py --once-json
  python tools/check_4B436630R_paper_sandbox_canary_reconciliation.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_mode_runtime_guardrail_4B436630S.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630S_paper_mode_runtime_guardrail.py --reports-dir .\reports\production_hardening

Expected ready decision:
  PAPER_MODE_RUNTIME_GUARDRAIL_READY_GUARDED_LOOP_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30S paper mode runtime guardrail"
  git tag -a 4B.4.3.6.6.30S -m "Accepted paper mode runtime guardrail"
  git push origin main
  git push origin 4B.4.3.6.6.30S

Risk posture:
  - Consumes latest valid 30R reconciliation ready report.
  - Runs guarded paper runtime loop only.
  - Strict caps enforce zero order/submit actions.
  - Kill-switch proof required.
  - No exchange submit.
  - No live-real.
