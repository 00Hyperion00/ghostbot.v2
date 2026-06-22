# 4B.4.3.6.6.32B Second Micro-Canary Submit Gate

- decision: `SECOND_MICRO_CANARY_SUBMIT_GATE_READY_SUBMIT_REQUEST_EVIDENCE_NO_LIVE_ORDER_SUBMIT`
- source_32a_release_candidate_review_verified: `True`
- min_notional_sizing_verified: `True`
- operator_submit_request_approval_verified: `True`
- candidate_symbol: `ETHUSDT`
- candidate_quantity: `0.0029`
- candidate_estimated_notional_usdt: `4.968744`
- approved_for_exchange_submit: `False`
- approved_for_second_micro_canary_order_submit: `False`
- patch_network_submit_attempted: `False`

## Risk note

32B creates submit-request evidence only. It must not submit an exchange order. A separate 32C live-submit phase is required for any real order.
