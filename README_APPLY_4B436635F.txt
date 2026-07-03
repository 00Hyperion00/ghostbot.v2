4B.4.3.6.6.35F — Public Data Collection Dry-Run

Scope:
- Collection Token Template
- Public Market Data Scope Freeze
- No-Submit Dry-Run Collector Guard

This patch is governance/planning-only. It does not start runtime evidence collection, public market-data collection, private API access, runtime probe, paper transition, live transition, order submit, runtime overlay, training/reload, archive execution, file move/delete, report delete, or deduplication.

Apply:
  python tools/apply_4B436635F_public_data_collection_dry_run.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436635F_public_data_collection_dry_run.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_public_data_collection_dry_run_4B436635F.py

Run reports:
  $env:PYTHONPATH="src"
  python tools/run_4B436635F_public_data_collection_dry_run.py --reports-dir .\reports\recovery --once-json
