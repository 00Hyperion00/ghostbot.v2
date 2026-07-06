# 4B.4.3.6.6.39F — Paper Sandbox Observation Runtime Metrics

Scope: observation runtime metrics contract / runtime still not started by patch / no network order / no live / no exchange submit.

Apply:

```powershell
python tools/apply_4B436639F_paper_sandbox_observation_runtime_metrics.py
```

Check:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436639F_paper_sandbox_observation_runtime_metrics.py --once-json
```

Test:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_paper_sandbox_observation_runtime_metrics_4B436639F.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

Run:

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436639F_paper_sandbox_observation_runtime_metrics.py --reports-dir .\reports\recovery --once-json
```

This patch does not start runtime, does not call `/health`, does not collect runtime metrics, does not submit orders, does not use private API, does not enable live-real, and does not enable exchange submit.
