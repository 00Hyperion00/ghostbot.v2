4B.4.3.6.6.33C Phase Chain Validator

APPLY

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633C_phase_chain_validator_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633C_phase_chain_validator.py

CHECK

$env:PYTHONPATH="src"
python tools/check_4B436633C_phase_chain_validator.py `
  --once-json

TEST

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q `
  tests/test_phase_chain_validator_4B436633C.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests

RUN REPORT

$env:PYTHONPATH="src"
python tools/run_4B436633C_phase_chain_validator.py `
  --reports-dir .\reports\recovery `
  --once-json

EXPECTED SAFETY STATE

approved_for_live_real=False
approved_for_paper_transition=False
approved_for_exchange_submit=False
approved_for_runtime_overlay=False
live_real_submit_allowed=False
network_submit_allowed=False
exchange_submit_allowed=False
runtime_overlay_allowed=False
trading_action_performed=False
training_performed=False
reload_performed=False
exchange_submit_performed=False

ROLLBACK

python tools/rollback_4B436633C_phase_chain_validator.py
