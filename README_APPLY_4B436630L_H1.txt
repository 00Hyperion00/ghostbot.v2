4B.4.3.6.6.30L-H1 Candidate Unlock Payload / Apply-Order Hotfix

Problem:
  The first 30L zip contained the 30L apply/check/run files only inside _patch_payload.
  Running python tools/apply_4B436630L_paper_sandbox_candidate_unlock_gate.py therefore failed because the top-level apply file did not exist.
  The extracted _patch_payload also made the existing 30I-H4 repo-hygiene checker fail through the 30K -> 30J -> 30I-H4 checker chain.

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630L_H1_candidate_unlock_payload_apply_order_hotfix.py --once-json
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
  git commit -m "4B.4.3.6.6.30L-H1 paper sandbox candidate unlock apply-order hotfix"
  git tag -a 4B.4.3.6.6.30L-H1 -m "Accepted paper sandbox candidate unlock apply-order hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30L-H1

Risk posture:
  - Candidate-only unlock proof.
  - No real paper execution.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
