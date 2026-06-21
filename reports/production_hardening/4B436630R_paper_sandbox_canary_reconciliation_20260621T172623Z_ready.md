# 4B.4.3.6.6.30R Paper Sandbox Canary Reconciliation

Consumes the 30Q canary order intent, verifies submit remained guarded, reconciles intent/fill/account as mismatch zero, and keeps live-real blocked.

## Decision
- `decision`: `PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL`
- `approved_for_paper_sandbox_canary_reconciliation`: `True`
- `source_30q_canary_gate_verified`: `True`
- `canary_order_intent_consumed`: `True`
- `intent_fill_account_reconciled`: `True`
- `submit_remained_guarded_verified`: `True`
- `mismatch_count`: `0`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`

## Reason codes
- `SOURCE_30Q_CANARY_ORDER_INTENT_VERIFIED`
- `CANARY_ORDER_INTENT_CONSUMED_SUBMIT_GUARDED`
- `INTENT_FILL_ACCOUNT_RECONCILED_MISMATCH_ZERO`
- `CANARY_SUBMIT_REMAINED_GUARDED_VERIFIED`
- `NO_LIVE_REAL_VERIFIED_CANARY_RECONCILIATION`
- `CANARY_RECONCILIATION_MISMATCH_ZERO_PROOF`
- `SUBMIT_REMAINED_GUARDED_PROOF`
- `NO_LIVE_REAL_VERIFIED`
