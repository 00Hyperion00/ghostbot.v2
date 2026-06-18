# 4B.4.3.6.6.28G-H6 HYP-006 No-Order Filter Shadow Overlay Design

This patch adds a fail-closed no-order review pack that reads the accepted H5 counterfactual ranking report and separates accepted candidates into primary overlay design candidates, quarantine-only tail-risk candidates, watchlist-low-sample candidates, rejected candidates, and explicit do-not-relax gate-combo blocklists.

## Contract

- Source contract: `4B.4.3.6.6.28G-H5`
- New contract: `4B.4.3.6.6.28G-H6`
- Report type: `hyp006_r1_no_order_filter_shadow_overlay_design_accepted_candidate_quarantine_review_pack`

## Safety stance

This patch does not change thresholds, scheduler tasks, runtime execution, training, reload, paper mode, live mode, or order routing. Runtime overlay activation is explicitly blocked.

Expected gates remain:

- `approved_for_parameter_relaxation_candidate = False`
- `approved_for_paper_candidate = False`
- `approved_for_live_real = False`
- `runtime_overlay_activation_performed = False`
- `training_performed = False`
- `reload_performed = False`
- `trading_action_performed = False`
- `order_actions_performed = False`

## Output

The runner writes:

- `reports/hyp006_r1_canonical/4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_*.json`
- `reports/hyp006_r1_canonical/4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_*.md`

## Intended interpretation

H6 is a design/review artifact only. It can approve a no-order filter shadow overlay candidate for review, but it cannot approve parameter relaxation, paper trading, live trading, or any order action.
