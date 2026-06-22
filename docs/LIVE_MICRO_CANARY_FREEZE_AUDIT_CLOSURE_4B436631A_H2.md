# 4B.4.3.6.6.31A-H2 Source-30Z Discovery Recovery

This hotfix fixes the 31A closure runner so it can consume the compact 30Z READY summary JSON produced during evidence recovery.

Risk invariants remain strict:

- 30Z READY decision is mandatory.
- 30Y-H1 reconciliation must be verified.
- PnL, fee and slippage evidence must be verified.
- Emergency stop continuity must be verified.
- No additional live order may be approved or performed.
- Patch network submit remains false.
- NOT_READY 31A evidence no longer writes an evidence-pack manifest.
