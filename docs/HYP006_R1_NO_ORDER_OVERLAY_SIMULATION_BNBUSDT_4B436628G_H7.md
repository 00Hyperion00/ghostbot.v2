# 4B.4.3.6.6.28G-H7 HYP-006 No-Order Overlay Simulation / BNBUSDT Primary Filter Shadow Measurement Pack

This patch adds a read-only no-order measurement pack for the H6 BNBUSDT primary overlay design candidate.

## Scope

- Reads the latest `4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_*.json` report.
- Extracts only the accepted primary BNBUSDT symbol overlay candidate.
- Measures the candidate as a no-order shadow overlay measurement pack using the H6 evidence row.
- Excludes quarantine, watchlist, rejected, and do-not-relax rows from the BNBUSDT primary measurement.
- Emits JSON and Markdown reports under `reports/hyp006_r1_canonical`.

## Safety contract

- No runtime overlay activation.
- No parameter relaxation.
- No scheduler mutation.
- No config mutation.
- No training or reload.
- No paper/live enablement.
- No order actions.

The only potentially true positive approval flag is `approved_for_overlay_shadow_measurement`. All trading and promotion gates remain fail-closed.
