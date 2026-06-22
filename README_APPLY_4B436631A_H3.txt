4B.4.3.6.6.31A-H3 — Explicit 30Z READY Source Override

Purpose
- Adds --source-30z-report to 31A runner.
- Consumes the exact valid 30Z READY JSON path instead of relying on discovery.
- Blocks READY unless the explicit 30Z file has 30Z contract + READY decision and no further live-order controls.
- Performs no exchange submit and approves no additional live order.

Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436631A_H3_explicit_30z_source_override_patch.zip" -DestinationPath . -Force
python tools/apply_4B436631A_H3_explicit_30z_source_override.py

Find exact 30Z READY path
$source30z = (Get-ChildItem .\reports\production_hardening\4B436630Z_post_live_micro_canary_risk_review_*_ready.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$source30z

Run corrected READY evidence
$env:PYTHONPATH="src"
python tools/run_4B436631A_live_micro_canary_freeze_audit_closure.py `
  --reports-dir .\reports\production_hardening `
  --source-30z-report $source30z `
  --operator-id operator-31a `
  --finalization-token FINALIZE_LIVE_MICRO_CANARY_AUDIT `
  --evidence-pack-id LIVE_MICRO_CANARY_8114595899_CLOSURE_H3 `
  --audit-comment "31A-H3: explicit valid 30Z READY source override; freeze micro-canary chain; no additional live order approved." `
  --acknowledge-hyp006-report-separation `
  --cleanup-bad-31a-not-ready-artifacts

Expected
LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY_EVIDENCE_PACK_SEALED_NO_FURTHER_LIVE_ORDER

Commit
git status --short
git add -A
git commit -m "4B.4.3.6.6.31A-H3 explicit 30Z source override for freeze audit closure"
git tag -a 4B.4.3.6.6.31A-H3 -m "Accepted 31A-H3 explicit 30Z source override"
git push origin main
git push origin 4B.4.3.6.6.31A-H3
