4B.4.3.6.6.27G-H4
No-Order Parameter Sensitivity Matrix / Near-Miss Threshold Stress Audit / Fail-Closed Research-Only Variant Report

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H4_no_order_parameter_sensitivity_matrix_near_miss_threshold_stress_audit_fail_closed_research_only_variant_report_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch doğrulaması:

python tools/apply_4B436627GH4_shadow_parameter_sensitivity_matrix.py

4) Read-only checker:

$env:PYTHONPATH="src"
python tools/check_4B436627GH4_shadow_parameter_sensitivity_matrix.py --once-json

5) Hedefli test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_shadow_parameter_sensitivity_matrix_4B436627GH4.py

6) Derleme kontrolü:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

7) Sensitivity matrix çalıştırma:

$latestLedger = Get-ChildItem `
  .\reports\hyp005_r1_canonical\4B436625X_hyp005_shadow_merged_ledger_*.jsonl |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$candidateSpec = Get-ChildItem `
  .\reports -Recurse -Filter "hyp005_r1_runtime_candidate_spec.json" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

python tools/run_4B436627GH4_shadow_parameter_sensitivity_matrix.py `
  --candidate-spec-json $candidateSpec.FullName `
  --ledger-jsonl $latestLedger.FullName `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --min-sweep-bps-values 18,15,12 `
  --min-wick-pct-values 42,38,35 `
  --max-compression-ratio-values 1.05,1.10,1.15 `
  --out-dir .\reports\hyp005_r1_canonical `
  --review-ok

Geri alma
=========

python tools/rollback_4B436627GH4_shadow_parameter_sensitivity_matrix.py

Güvenlik
========

Bu patch read-only araştırma raporudur. Paper/live/order/training/reload açmaz.
