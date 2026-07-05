4B.4.3.6.6.38H-H1 Observation Metrics Source Report Selection Hotfix

Purpose:
- Fixes 38H source gate selection so 38G main *_ready.json is preferred.
- Excludes 38G gate/probe/contract/snapshot/guard artifacts from source selection.
- Keeps runtime process start, runtime health probe, network order, live, exchange submit, private API and signed requests disabled.

Apply:
python tools/apply_4B436638H_H1_observation_metrics_source_report_selection_hotfix.py

Then rerun original 38H commands:
python tools/check_4B436638H_paper_sandbox_observation_metrics_gate.py --once-json
python -m pytest -q tests/test_paper_sandbox_observation_metrics_gate_4B436638H.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
python tools/run_4B436638H_paper_sandbox_observation_metrics_gate.py --reports-dir .\reports\recovery --once-json
