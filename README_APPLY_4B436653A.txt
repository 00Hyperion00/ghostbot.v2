# 4B.4.3.6.6.53A — Paper Sandbox Controlled Paper Trading Soak Evidence Review

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436653A_paper_sandbox_controlled_paper_trading_soak_evidence_review.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436653A_paper_sandbox_controlled_paper_trading_soak_evidence_review.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436653A_paper_sandbox_controlled_paper_trading_soak_evidence_review.py --reports-dir .\reports\recovery --once-json
```
