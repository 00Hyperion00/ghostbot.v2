# HYP-005 Baseline Evidence Freeze / Refined Candidate Revalidation Planning Gate

- contract_version: `4B.4.3.6.6.25AD`
- decision: `HYP005_R1_REVALIDATION_PLANNING_READY`
- generated_at_utc: `2026-06-02T07:28:34Z`
- source_25ac_report: `reports\4B436625AC_hyp005_symbol_risk_pruning_decision_20260602_071442.json`
- source_25ac_report_sha256: `20893869ca14fe88bd4112f2f006556c48dbe17f4d091f3c5dac9590fb34cccb`
- baseline_evidence_digest_sha256: `08180fa14b6f13791c4edca7dd7c0249b90c52b93a5dedc96c2f91d6261d3851`
- refined_branch_id: `HYP-005-R1`
- fresh_ledger_namespace: `HYP005_R1`
- starting_unique_shadow_observation_count: `0`
- shadow_sample_target: `30`
- recommended_pruned_symbols: `AVAXUSDT,DOGEUSDT`
- recommended_refined_symbols_arg: `ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT`

## Safety

- Baseline evidence is frozen by a write-once timestamped snapshot plus SHA-256 digest.
- Legacy baseline observations are not reused in HYP-005-R1.
- Scheduler regeneration requires a separate operator-reviewed 25AE patch.
- This gate does not mutate scheduler configuration.
- This gate does not train or reload a model.
- This gate does not start paper trading.
- This gate does not enable live trading.
- This gate does not send POST requests or orders.
- Paper/live remain blocked.

## Reason codes

- `BASELINE_EVIDENCE_FROZEN`
- `BASELINE_SCHEDULER_DISABLE_BEFORE_REGENERATION_REQUIRED`
- `HYP005_R1_FRESH_LEDGER_NAMESPACE_DECLARED`
- `LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED`
- `NO_AUTOMATIC_SCHEDULER_CONFIG_MUTATION`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `REFINED_CANDIDATE_REVALIDATION_PLANNED`
- `SCHEDULER_REGENERATION_REQUIRES_SEPARATE_OPERATOR_PATCH`
- `SOURCE_25AC_BRANCH_REFINEMENT_REQUIRED_CONFIRMED`

## Recommendation

HYP-005 baseline evidence is frozen and HYP-005-R1 fresh no-order revalidation planning is ready. Keep paper/live/order disabled. Disable the baseline scheduler before a separate operator-reviewed 25AE scheduler pack is registered. Do not reuse legacy baseline observations in the refined branch.
