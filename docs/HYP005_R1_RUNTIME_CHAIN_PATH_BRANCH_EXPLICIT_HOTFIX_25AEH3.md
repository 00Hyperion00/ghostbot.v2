# 4B.4.3.6.6.25AE-H3 — HYP-005-R1 Runtime Chain Path Safety / Branch Compatibility / Explicit Chaining Hotfix

This hotfix closes the runtime defects discovered after the isolated HYP-005-R1 scheduler pack was registered.

## Fixes

- Generated PowerShell file discovery uses `Join-Path`; backslash-plus-digit control-character corruption is removed.
- The R1 runtime candidate keeps the canonical `branch_name=liquidity_sweep_reversal_vol_compression` expected by 25V.
- R1 identity remains explicit in `refined_branch_id=HYP-005-R1`, `fresh_ledger_namespace=HYP005_R1`, and `candidate_variant=r1_pruned_symbol_revalidation` metadata.
- 25W supports `--collection-report-json` and strict scoped chaining.
- 25X, 25W, and 25Y support `--strict-explicit-chain`; discovery fallback is disabled when the generated R1 cycle uses this mode.
- The first empty-ledger cycle is allowed to complete safely and emit scoped BLOCK reports without enabling paper/live/order actions.

## Safety contract

- Baseline task remains Disabled.
- Existing R1 task must be Disabled before replacement registration.
- `reports\hyp005_r1_isolated` is the only R1 runtime reports directory.
- Baseline reports and ledgers are never imported into HYP-005-R1.
- Paper/live/order/training/reload remain blocked.
