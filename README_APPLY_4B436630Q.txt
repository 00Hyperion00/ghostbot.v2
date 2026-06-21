4B.4.3.6.6.30Q First Paper Sandbox Canary Submit Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630Q_first_paper_sandbox_canary_submit_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630Q_first_paper_sandbox_canary_submit_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630Q_first_paper_sandbox_canary_submit_gate.py --once-json
  python tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_first_paper_sandbox_canary_submit_gate_4B436630Q.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py --reports-dir .\reports\production_hardening

Expected default decision:
  FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_OPERATOR_APPROVAL_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Explicit operator canary approval + order intent:
  $env:PYTHONPATH="src"
  python tools/run_4B436630Q_first_paper_sandbox_canary_submit_gate.py --reports-dir .\reports\production_hardening --operator-id operator-30q --approval-token APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE --issue-canary-approval --write-intent

Expected ready decision:
  FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL

Commit only if all checks pass and evidence is READY:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30Q first paper sandbox canary submit gate"
  git tag -a 4B.4.3.6.6.30Q -m "Accepted first paper sandbox canary submit gate"
  git push origin main
  git push origin 4B.4.3.6.6.30Q

Risk posture:
  - Single sandbox/demo canary order intent only.
  - Exchange submit path remains guarded.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
