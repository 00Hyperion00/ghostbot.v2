4B.4.3.6.6.31A Live Micro-Canary Freeze & Audit Closure

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436631A_live_micro_canary_freeze_audit_closure_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436631A_live_micro_canary_freeze_audit_closure.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436631A_live_micro_canary_freeze_audit_closure.py --once-json
  python tools/check_4B436630Z_post_live_micro_canary_risk_review.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_live_micro_canary_freeze_audit_closure_4B436631A.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default evidence, operator audit required:
  $env:PYTHONPATH="src"
  python tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py --reports-dir .\reports\production_hardening

READY evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py `
    --reports-dir .\reports\production_hardening `
    --operator-id operator-31a `
    --finalization-token FINALIZE_LIVE_MICRO_CANARY_AUDIT `
    --evidence-pack-id LIVE_MICRO_CANARY_8114595899_CLOSURE `
    --audit-comment "Freeze micro-canary chain after 30Z; no additional live order approved." `
    --acknowledge-hyp006-report-separation

Expected READY decision:
  LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY_EVIDENCE_PACK_SEALED_NO_FURTHER_LIVE_ORDER

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.31A live micro-canary freeze audit closure"
  git tag -a 4B.4.3.6.6.31A -m "Accepted live micro-canary freeze audit closure"
  git push origin main
  git push origin 4B.4.3.6.6.31A

Risk: this phase seals evidence and freezes live micro-canary state. It does not approve or perform any further live order.
