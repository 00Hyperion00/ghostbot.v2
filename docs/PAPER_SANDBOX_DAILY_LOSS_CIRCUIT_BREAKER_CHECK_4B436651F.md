    # 4B.4.3.6.6.51F — Paper Sandbox Daily Loss Circuit Breaker Check

    Decision: `PAPER_SANDBOX_CONTROLLED_PAPER_SUBMIT_FINAL_PREFLIGHT_DAILY_LOSS_CIRCUIT_BREAKER_CHECK_READY_REVIEW_AND_CONTRACT_ONLY_PAPER_SUBMIT_NOT_ENABLED_BY_PATCH_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.51E (4B436651E)`

    Next: `4B.4.3.6.6.51G — Paper Sandbox Duplicate Order Idempotency Lock Check`

    ## Safety rules
    - 4B.4.3.6.6.51E (4B436651E) READY source is required
- 4B.4.3.6.6.51F is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.51G is not auto-unlocked by 4B.4.3.6.6.51F
