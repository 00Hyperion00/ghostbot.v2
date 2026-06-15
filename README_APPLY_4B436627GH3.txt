4B.4.3.6.6.27G-H3
Shadow Observation Stagnation Diagnostics / Candidate Signal Near-Miss Audit / No-Order Research Bottleneck Report

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H3_shadow_observation_stagnation_diagnostics_candidate_signal_near_miss_audit_no_order_research_bottleneck_report_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch verifier/apply:

python tools/apply_4B436627GH3_shadow_stagnation_diagnostics.py

4) Read-only checker:

$env:PYTHONPATH="src"
python tools/check_4B436627GH3_shadow_stagnation_diagnostics.py --once-json

5) Hedefli test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_shadow_stagnation_diagnostics_4B436627GH3.py

6) Derleme kontrolü:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

7) Güncel latest ledger ve candidate spec ile no-order diagnostics çalıştırma:

$latestLedger = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436625X_hyp005_shadow_merged_ledger_*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$candidateSpec = Get-ChildItem `
  .\reports -Recurse -Filter "hyp005_r1_runtime_candidate_spec.json" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python tools/run_4B436627GH3_shadow_stagnation_diagnostics.py `
  --candidate-spec-json $candidateSpec.FullName `
  --ledger-jsonl $latestLedger.FullName `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --out-dir .\reports\hyp005_r1_canonical `
  --review-ok

8) Son raporu oku:

$latestGh3 = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436627GH3_hyp005_shadow_stagnation_diagnostics_*.json |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content $latestGh3.FullName -Raw -Encoding UTF8

Geri alma
=========

python tools/rollback_4B436627GH3_shadow_stagnation_diagnostics.py

Notlar
======

- Bu patch scheduler cadence değiştirmez.
- Config değiştirmez.
- Training/reload yapmaz.
- Paper/live açmaz.
- Order göndermez.
- Public market data GET dışında network işlemi tasarlanmamıştır.
