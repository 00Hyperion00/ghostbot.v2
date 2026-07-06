# 4B.4.3.6.6.51E — Paper Sandbox Max Notional Quantity Trade Count Caps Check

Review/contract gate only. This patch does not start runtime, enable paper submit, perform paper/network order, approve live-real, access private APIs, or enable exchange-submit.

## Apply
```powershell
python tools/apply_4B436651E_paper_sandbox_max_notional_quantity_trade_count_caps_check.py
```

## Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436651E_paper_sandbox_max_notional_quantity_trade_count_caps_check.py --once-json
```

## Run report
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436651E_paper_sandbox_max_notional_quantity_trade_count_caps_check.py --reports-dir .\reports\recovery --once-json
```
