# 4B.4.3.6.6.54H — Paper Sandbox Controlled Paper Trading Soak Acceptance Decision Gate

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436654H_paper_sandbox_controlled_paper_trading_soak_acceptance_decision_gate.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436654H_paper_sandbox_controlled_paper_trading_soak_acceptance_decision_gate.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436654H_paper_sandbox_controlled_paper_trading_soak_acceptance_decision_gate.py --reports-dir .\reports\recovery --once-json
```
