4B.4.3.6.6.31A-H2 — 31A source-30Z discovery recovery hotfix

Purpose
- Accepts the compact 30Z READY JSON summary produced by the post-live micro-canary risk review runner.
- Strictly requires 30Z READY decision, source 30Y-H1 reconciliation, PnL/fee/slippage evidence, emergency stop continuity, and no additional live order.
- Prevents evidence-pack manifest write for NOT_READY 31A evidence.
- Adds optional cleanup for bad 31A not_ready artifacts.
- Does not submit orders and does not approve additional live-real continuation.

Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436631A_H2_source_30z_discovery_recovery_patch.zip" -DestinationPath . -Force
python tools/apply_4B436631A_H2_source_30z_discovery_recovery.py

Check/test
$env:PYTHONPATH="src"
python tools/check_4B436631A_H2_source_30z_discovery_recovery.py --once-json
python tools/check_4B436631A_live_micro_canary_freeze_audit_closure.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_live_micro_canary_freeze_audit_closure_4B436631A.py tests/test_live_micro_canary_freeze_audit_closure_4B436631A_H2.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Regenerate corrected READY evidence
$env:PYTHONPATH="src"
python tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py `
  --reports-dir .\reports\production_hardening `
  --operator-id operator-31a `
  --finalization-token FINALIZE_LIVE_MICRO_CANARY_AUDIT `
  --evidence-pack-id LIVE_MICRO_CANARY_8114595899_CLOSURE_H2 `
  --audit-comment "31A-H2: consume valid 30Z READY summary; freeze micro-canary chain; no additional live order approved." `
  --acknowledge-hyp006-report-separation `
  --cleanup-bad-31a-not-ready-artifacts

Expected decision
LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY_EVIDENCE_PACK_SEALED_NO_FURTHER_LIVE_ORDER

Commit

git status --short
git add -A
git commit -m "4B.4.3.6.6.31A-H2 recover 30Z discovery for freeze audit closure"
git tag -a 4B.4.3.6.6.31A-H2 -m "Accepted 31A-H2 source 30Z discovery recovery"
git push origin main
git push origin 4B.4.3.6.6.31A-H2
