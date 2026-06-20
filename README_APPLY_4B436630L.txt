4B.4.3.6.6.30L Paper Sandbox Candidate Unlock Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630L_paper_sandbox_candidate_unlock_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py --once-json
  python tools/check_4B436630K_paper_sandbox_operator_final_go_no_go_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_candidate_unlock_gate_4B436630L.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py --reports-dir .\reports\production_hardening

Expected default decision:
  PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_EXPLICIT_UNLOCK_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Explicit candidate unlock report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630L_paper_sandbox_candidate_unlock_gate.py --reports-dir .\reports\production_hardening --operator-id operator-30l --unlock-token UNLOCK_PAPER_SANDBOX_CANDIDATE --issue-candidate-unlock

Expected ready decision:
  PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30L paper sandbox candidate unlock gate"
  git tag -a 4B.4.3.6.6.30L -m "Accepted paper sandbox candidate unlock gate"
  git push origin main
  git push origin 4B.4.3.6.6.30L

Risk posture:
  - Paper sandbox candidate can be unlocked as candidate-only.
  - No paper sandbox dry-run execution enablement.
  - No exchange submit.
  - No live-real approval.
  - No runtime overlay/training/reload/strategy mutation.
