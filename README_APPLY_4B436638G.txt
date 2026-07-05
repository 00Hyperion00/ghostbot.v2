4B.4.3.6.6.38G — Paper Sandbox Local Runtime Health Evidence

Scope:
- Local health evidence contract only.
- No runtime process start.
- No runtime health probe execution.
- No network order.
- No live-real.
- No exchange submit.

Apply:
  python tools/apply_4B436638G_paper_sandbox_local_runtime_health_evidence.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436638G_paper_sandbox_local_runtime_health_evidence.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_local_runtime_health_evidence_4B436638G.py

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436638G_paper_sandbox_local_runtime_health_evidence.py --reports-dir .\reports\recovery --once-json
