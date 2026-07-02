4B.4.3.6.6.33D-H1 — Destructive Endpoint Guard Coverage Hotfix

Uygulama:

  python tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py

Kontrol:

  $env:PYTHONPATH="src"
  python tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py --once-json
  python -m pytest -q tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Rapor üret:

  $env:PYTHONPATH="src"
  python tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py --reports-dir .\reports\recovery --once-json

33D tekrar doğrula:

  $env:PYTHONPATH="src"
  python tools/check_4B436633D_runtime_safety_lockdown.py --once-json
  python tools/run_4B436633D_runtime_safety_lockdown.py --reports-dir .\reports\recovery --once-json

Bu hotfix emir, exchange submit, runtime overlay, training veya reload yapmaz.
