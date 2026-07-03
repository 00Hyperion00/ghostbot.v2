# 4B.4.3.6.6.37B — Install Contract Alignment

Scope:
- Source gate: 37A READY re-baseline.
- Generate/align `requirements.txt` from `pyproject.toml` `[project].dependencies`.
- Add a bounded README install-contract section.
- Normalize known Windows launcher install command references where launcher files exist.
- Emit install-contract alignment, P0 gap closure delta, and no-submit P0-1 hardening gate reports.

Safety boundary:
- No exchange/network/order submit.
- No public market-data collection.
- No runtime evidence collection.
- No runtime probe.
- No private API/account read.
- No paper/live/live-real enablement.
- No runtime overlay/training/reload.
- No archive/delete/move/deduplication.
- 37C is not auto-unlocked.

Expected decision:
`INSTALL_CONTRACT_ALIGNMENT_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_1_LOCKED`
