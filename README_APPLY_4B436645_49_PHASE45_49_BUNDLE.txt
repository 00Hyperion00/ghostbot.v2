4B.4.3.6.6.45-49 — Phase 45-49 Paper Sandbox Transition Bundle

Apply:
  python tools/apply_4B436645_49_phase45_to_phase49_paper_sandbox_transition_bundle.py

Check:
  python tools/check_4B436645_49_phase45_to_phase49_paper_sandbox_transition_bundle.py --once-json

Run:
  python tools/run_4B436645_49_phase45_to_phase49_paper_sandbox_transition_bundle.py --reports-dir .\reports\recovery --once-json

Test:
  python -m pytest -q tests/test_phase45_to_phase49_paper_sandbox_transition_bundle_4B436645_49.py

This patch performs no runtime start, no actual evidence intake, no paper submit, no network order, no live-real, no exchange submit, no git mutation, and no destructive cleanup.
