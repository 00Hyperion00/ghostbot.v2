4B.4.3.6.6.39B Paper Sandbox Runtime Start Command Contract

Amaç:
- 39A READY raporu üstüne paper sandbox runtime start command contract üretir.
- Runtime start command template sadece declare edilir.
- Command execution, runtime process start, network order, live-real ve exchange submit yapılmaz.

Uygulama:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436639B_paper_sandbox_runtime_start_command_contract_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436639B_paper_sandbox_runtime_start_command_contract.py

Kontrol:
$env:PYTHONPATH="src"
python tools/check_4B436639B_paper_sandbox_runtime_start_command_contract.py --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_paper_sandbox_runtime_start_command_contract_4B436639B.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
$env:PYTHONPATH="src"
python tools/run_4B436639B_paper_sandbox_runtime_start_command_contract.py --reports-dir .\reports\recovery --once-json
