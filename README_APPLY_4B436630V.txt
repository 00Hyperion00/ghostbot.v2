4B.4.3.6.6.30V Live-Real Preflight Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive `
    -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630V_live_real_preflight_gate_patch.zip" `
    -DestinationPath . `
    -Force
  python tools/apply_4B436630V_live_real_preflight_gate.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436630V_live_real_preflight_gate.py --once-json
  python tools/check_4B436630U_paper_promotion_review.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_live_real_preflight_gate_4B436630V.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630V_live_real_preflight_gate.py `
    --reports-dir .\reports\production_hardening

Expected decision:
  LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30V live-real preflight gate"
  git tag -a 4B.4.3.6.6.30V -m "Accepted live-real preflight gate"
  git push origin main
  git push origin 4B.4.3.6.6.30V

Risk contract:
  Preflight only. No live-real order. No exchange submit. No network submit attempt.
  API key/secret values are never persisted; only redacted presence flags are reported.
