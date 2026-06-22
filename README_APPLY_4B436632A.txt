# 4B.4.3.6.6.32A Apply Guide

Post-Freeze Release Candidate Review — final audit snapshot review / live-real continuation risk decision / capital cap confirmation / second micro-canary eligibility gate / no live order submit.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436632A_post_freeze_release_candidate_review_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436632A_post_freeze_release_candidate_review.py
```

## Check and test

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436632A_post_freeze_release_candidate_review.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_post_freeze_release_candidate_review_4B436632A.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## 31B READY source path

```powershell
$source31b = (
  Get-ChildItem .\reports\production_hardening\4B436631B_release_hygiene_bad_evidence_ledger_cleanup_*_ready.json |
    Where-Object { $_.Name -notlike "*_not_ready.json" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
).FullName

$source31b
```

## READY evidence

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436632A_post_freeze_release_candidate_review.py `
  --reports-dir .\reports\production_hardening `
  --source-31b-report $source31b `
  --operator-id operator-32a `
  --finalization-token FINALIZE_32A_RELEASE_CANDIDATE_REVIEW `
  --emergency-stop-armed `
  --capital-cap-usdt 25 `
  --second-micro-max-notional-usdt 5 `
  --daily-loss-limit-usdt 5 `
  --max-slippage-bps 50 `
  --audit-comment "32A: post-freeze release candidate review; second micro-canary candidate only; no live order submit."
```

Expected decision:

```text
POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY_SECOND_MICRO_CANARY_ELIGIBILITY_GATE_NO_LIVE_ORDER_SUBMIT
```

## Commit

```powershell
git status --short

git add -A

git commit -m "4B.4.3.6.6.32A post-freeze release candidate review"

git tag -a 4B.4.3.6.6.32A `
  -m "Accepted post-freeze release candidate review"

git push origin main
git push origin 4B.4.3.6.6.32A
```

Risk note: 32A does not submit to Binance and does not approve a live-real order. It only creates a candidate eligibility gate for a future, separate order-submit phase.
