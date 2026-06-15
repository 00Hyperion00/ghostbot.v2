$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\muhas\OneDrive\Masaüstü\trade_botV2'
$env:PYTHONPATH = 'src'

& 'C:\Users\muhas\AppData\Local\Programs\Python\Python314\python.exe' `
  'tools/run_4B436628D_hyp006_canonical_shadow_cycle.py' `
  --registration-approval-json 'C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp006_r1_canonical\4B436628D_hyp006_r1_shadow_collection_registration_approval_20260615T182346Z.json' `
  --registration-json 'C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp006_r1_candidate_spec\4B436628B_hyp006_r1_candidate_spec_registration_gate_20260615T171622Z.json' `
  --symbols 'ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT' `
  --interval '4h' `
  --days 30 `
  --out-dir 'reports\hyp006_r1_canonical' `
  --review-ok `
  1>> 'C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp006_r1_canonical\hyp006_scheduler_stdout.log' `
  2>> 'C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp006_r1_canonical\hyp006_scheduler_stderr.log'

exit $LASTEXITCODE