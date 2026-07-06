4B.4.3.6.6.40 — Phase 40 Runtime Start Execution Authorization Bundle

This bundle contains 40A through 40I as separate gated patches.

Apply bundle:
  python tools/apply_4B436640_phase40_runtime_start_execution_authorization_bundle.py

Check bundle:
  set PYTHONPATH=src
  python tools/check_4B436640_phase40_runtime_start_execution_authorization_bundle.py --once-json

Run bundle reports:
  set PYTHONPATH=src
  python tools/run_4B436640_phase40_runtime_start_execution_authorization_bundle.py --reports-dir .\reports\recovery --once-json

Run tests:
  set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  set PYTHONPATH=src
  python -m pytest -q tests/test_phase40_runtime_start_execution_authorization_bundle_4B436640.py tests/test_paper_sandbox_runtime_start_execution_authorization_review_4B436640A.py tests/test_paper_sandbox_typed_runtime_start_operator_approval_4B436640B.py tests/test_paper_sandbox_runtime_start_pre_execution_gate_4B436640C.py tests/test_paper_sandbox_single_instance_runtime_lock_validation_4B436640D.py tests/test_paper_sandbox_controlled_runtime_start_command_package_4B436640E.py tests/test_paper_sandbox_local_runtime_process_start_evidence_4B436640F.py tests/test_paper_sandbox_runtime_health_probe_actual_evidence_gate_4B436640G.py tests/test_paper_sandbox_observation_runtime_metrics_actual_evidence_gate_4B436640H.py tests/test_paper_sandbox_runtime_start_execution_closure_4B436640I.py

Safety guarantees:
  runtime start command execution = false
  runtime process start = false
  paper runtime start = false
  paper order submit = false
  network order submit = false
  live-real = false
  exchange submit = false
  next phase auto unlock = false
