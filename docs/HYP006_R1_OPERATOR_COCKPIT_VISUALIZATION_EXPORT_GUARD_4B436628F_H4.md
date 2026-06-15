# 4B.4.3.6.6.28F-H4 Operator Cockpit Visualization / Export Guard Hotfix

Read-only hotfix for HYP-006-R1 operator cockpit parity.

- Adds cumulative sample timeline field for a rising 1..N progress line.
- Adds no-order MAE/MFE proxy scatter when true execution MAE/MFE is not collected.
- Suppresses legacy HYP-005 active audit source labels.
- Marks risk-sizing evidence export as unavailable/fail-closed with `RISK_SIZING_RUNTIME_EVENT_NOT_FOUND`.
- Does not mutate config, scheduler, model, training, reload, paper/live, or order state.
