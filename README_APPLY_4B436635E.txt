4B.4.3.6.6.35E — Dry-Run Collection Authorization

Purpose:
- Validate the 35D collection preflight gate as the source gate.
- Produce an Operator Collection Token Ledger.
- Produce a Public Data Dry-Run Authorization ledger.
- Produce a No-Submit Collection Seal.

Safety boundary:
- No runtime evidence collection is started.
- No public market-data collection is performed.
- No runtime probe is performed.
- No private API/account read is allowed or performed.
- No paper/live/submit/runtime overlay transition is approved.

Apply:
  python tools/apply_4B436635E_dry_run_collection_authorization.py

Check:
  set PYTHONPATH=src
  python tools/check_4B436635E_dry_run_collection_authorization.py --once-json

Run:
  set PYTHONPATH=src
  python tools/run_4B436635E_dry_run_collection_authorization.py --reports-dir .\reports\recovery --once-json
