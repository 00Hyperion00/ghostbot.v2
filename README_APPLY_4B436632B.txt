# 4B.4.3.6.6.32B Second Micro-Canary Submit Gate

Evidence-only submit gate. No live exchange submit is performed.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436632B_second_micro_canary_submit_gate_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436632B_second_micro_canary_submit_gate.py
```

## Check and test

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436632B_second_micro_canary_submit_gate.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_second_micro_canary_submit_gate_4B436632B.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## Get 32A READY source

```powershell
$source32a = (
  Get-ChildItem .\reports\production_hardening\4B436632A_post_freeze_release_candidate_review_*_ready.json |
    Where-Object { $_.Name -notlike "*_not_ready.json" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
).FullName

$source32a
```

## Generate submit-request evidence only

This creates a candidate request artifact but does not submit to Binance.

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436632B_second_micro_canary_submit_gate.py `
  --reports-dir .\reports\production_hardening `
  --source-32a-report $source32a `
  --operator-id operator-32b `
  --finalization-token FINALIZE_32B_SECOND_MICRO_CANARY_SUBMIT_GATE `
  --operator-approval-id OPERATOR_APPROVES_32B_SUBMIT_REQUEST_ONLY `
  --operator-approve-submit-request `
  --emergency-stop-armed `
  --symbol ETHUSDT `
  --side BUY `
  --order-type MARKET `
  --reference-price 1713.36 `
  --requested-notional-usdt 4.95 `
  --exchange-min-notional-usdt 4.95 `
  --quantity-step 0.0001 `
  --min-quantity 0.0001 `
  --audit-comment "32B: evidence-only second micro-canary submit request gate; no live order submit."
```

Expected decision:

```text
SECOND_MICRO_CANARY_SUBMIT_GATE_READY_SUBMIT_REQUEST_EVIDENCE_NO_LIVE_ORDER_SUBMIT
```

## Commit

```powershell
git status --short

git add -A

git commit -m "4B.4.3.6.6.32B second micro-canary submit gate"

git tag -a 4B.4.3.6.6.32B `
  -m "Accepted second micro-canary submit gate"

git push origin main
git push origin 4B.4.3.6.6.32B
```
