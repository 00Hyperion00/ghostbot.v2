# 4B.4.3.6.6.25AD — HYP-005 Baseline Evidence Freeze / Refined Candidate Revalidation Planning Gate

## Purpose

This patch consumes the latest 25AC `HYP005_BRANCH_REFINEMENT_REQUIRED` report, freezes the 10-symbol HYP-005 baseline evidence with a timestamped SHA-256 snapshot, and plans a separate `HYP-005-R1` no-order revalidation branch.

The refined candidate removes the 25AC risk-pruning recommendation symbols and starts a new ledger namespace with zero carried-forward observations.

## Fresh-ledger contract

- Refined branch id: `HYP-005-R1`
- Fresh ledger namespace: `HYP005_R1`
- Starting unique shadow observation count: `0`
- Legacy baseline observation reuse: prohibited
- Default new unique shadow sample target: `30`
- Proposed next scheduler-pack contract: `4B.4.3.6.6.25AE`

## Safety contract

- Planning-only gate.
- Reads the latest 25AC report or an explicit `--input-json` report.
- Freezes baseline evidence using a write-once timestamped snapshot and SHA-256 digest.
- Does not mutate scheduler configuration.
- Does not disable or register a Windows scheduled task.
- Does not regenerate the scheduler pack.
- Does not train or reload a model.
- Does not start paper trading.
- Does not enable live trading.
- Does not send POST requests or orders.
- Paper/live remain blocked.

The baseline scheduler should be disabled manually before a separate operator-reviewed 25AE scheduler regeneration pack is registered.

## Decisions

- `HYP005_R1_REVALIDATION_PLANNING_READY`
- `HYP005_R1_REVALIDATION_PLANNING_BLOCK`

## Outputs

- `4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_*.json`
- `4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_*.md`
- `4B436625AD_hyp005_baseline_evidence_freeze_*.json`
- `4B436625AD_hyp005_r1_refined_candidate_revalidation_plan_*.json`
