# 4B.4.3.6.6.32B Second Micro-Canary Submit Gate

This patch adds an evidence-only submit gate for a second live micro-canary candidate.

## Hard risk contract

- No Binance submit is performed.
- No network submit is attempted.
- No live-real order is approved by this patch.
- 32B may create only a submit-request evidence object.
- Any actual exchange submit requires a separate 32C live-submit phase.

## Required source

32B consumes an accepted `4B.4.3.6.6.32A` post-freeze release candidate review report.

## Required operator inputs

- `--operator-id`
- `--finalization-token FINALIZE_32B_SECOND_MICRO_CANARY_SUBMIT_GATE`
- `--operator-approval-id`
- `--operator-approve-submit-request`
- `--emergency-stop-armed`
- market sizing inputs: reference price, requested notional, exchange min-notional, quantity step, min quantity

## Fail-closed sizing

If quantity rounding causes estimated notional to exceed the `32A` second micro cap, 32B returns NOT_READY and creates no submit request.
