# 4B.4.3.6.6.39D — Paper Sandbox Local Runtime Process Start Gate

Scope: local runtime process start gate / explicit authorization evidence validation / command still not executed unless gate approves / no network order / no live / no exchange submit.

Apply:

```powershell
python tools/apply_4B436639D_paper_sandbox_local_runtime_process_start_gate.py
```

Check:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436639D_paper_sandbox_local_runtime_process_start_gate.py --once-json
```

Test:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_paper_sandbox_local_runtime_process_start_gate_4B436639D.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

Run:

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436639D_paper_sandbox_local_runtime_process_start_gate.py --reports-dir .\reports\recovery --once-json
```

This patch validates explicit authorization evidence from 39C and defines the local runtime process start gate. It does not execute the runtime start command, does not start a process, does not submit orders, does not use private API, does not enable live-real, and does not enable exchange submit.
