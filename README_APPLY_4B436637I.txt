4B.4.3.6.6.37I — Fee / Slippage Baseline

Scope:
- Maker/taker fee model baseline
- Slippage fail-closed guard
- Break-even cost floor
- No-Submit Production Hardening P0-8

Apply:
python tools/apply_4B436637I_fee_slippage_baseline.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436637I_fee_slippage_baseline.py --once-json

Tests:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_fee_slippage_baseline_4B436637I.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
$env:PYTHONPATH="src"
python tools/run_4B436637I_fee_slippage_baseline.py --reports-dir .eportsecovery --once-json

Safety:
- No live/paper submit
- No exchange/network/order submit
- No market data lookup
- No account fee-tier lookup
- No runtime binding
- No runtime start/reload/training
