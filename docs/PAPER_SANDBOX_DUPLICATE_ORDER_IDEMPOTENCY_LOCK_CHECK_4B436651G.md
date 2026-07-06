    # 4B.4.3.6.6.51G — Paper Sandbox Duplicate Order Idempotency Lock Check

    Decision: `PAPER_SANDBOX_CONTROLLED_PAPER_SUBMIT_FINAL_PREFLIGHT_DUPLICATE_ORDER_IDEMPOTENCY_LOCK_CHECK_READY_REVIEW_AND_CONTRACT_ONLY_PAPER_SUBMIT_NOT_ENABLED_BY_PATCH_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.51F (4B436651F)`

    Next: `4B.4.3.6.6.51H — Paper Sandbox Controlled Paper Submit Final Preflight Decision Gate`

    ## Safety rules
    - 4B.4.3.6.6.51F (4B436651F) READY source is required
- 4B.4.3.6.6.51G is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.51H is not auto-unlocked by 4B.4.3.6.6.51G
