# 4B.4.3.6.6.25AE-H2 — HYP-005-R1 Reports-Dir Isolation / Fresh Ledger Runtime Chain Hotfix

## Purpose

This hotfix prevents HYP-005-R1 refined-branch evidence from reading project-level baseline reports or ledgers.

## Isolation contract

- Runtime reports directory: `reports\hyp005_r1_isolated`.
- Project-level `reports` root is forbidden as an R1 runtime input.
- 25V writes only to the isolated R1 directory.
- 25X reads only the isolated logger report and ledger, then writes only to the isolated R1 directory.
- 25W reads only the isolated R1 directory and explicitly chained R1 logger report.
- 25Y reads only the isolated R1 directory and explicitly chained R1 logger, collection, and acceptance reports.
- Legacy baseline reports and observations are not reused.
- Existing R1 Windows task must be disabled before H2 replacement registration.

## Safety

Paper/live/order/training/reload remain blocked. No Windows task is automatically mutated by the patch or pack generator.
