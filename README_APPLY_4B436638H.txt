4B.4.3.6.6.38H Paper Sandbox Observation Metrics Gate

Purpose:
- Add static observation metrics gate evidence for paper sandbox transition review.
- Verify 38G READY source evidence.
- Keep runtime process start, runtime health probe, network order, live-real and exchange submit locked.

Apply:
python tools/apply_4B436638H_paper_sandbox_observation_metrics_gate.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436638H_paper_sandbox_observation_metrics_gate.py --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_paper_sandbox_observation_metrics_gate_4B436638H.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
$env:PYTHONPATH="src"
python tools/run_4B436638H_paper_sandbox_observation_metrics_gate.py --reports-dir .\reports\recovery --once-json
