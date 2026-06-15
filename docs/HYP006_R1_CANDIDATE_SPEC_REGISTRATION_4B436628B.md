# 4B.4.3.6.6.28B HYP-006-R1 Candidate Spec Draft

Purpose: produce a fail-closed HYP-006-R1 candidate spec draft and no-order shadow registration gate from the accepted 28A discovery pack.

This patch is additive and read-only. It does not mutate config, branch state, scheduler tasks, training, model reload, paper/live state, or order routing.

## Safety

- `approved_for_shadow_collection = false`
- `approved_for_training_candidate = false`
- `approved_for_paper_candidate = false`
- `approved_for_live_real = false`
- `order_actions_performed = false`
- `scheduler_mutation_performed = false`

The output can only proceed to `28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL`.
