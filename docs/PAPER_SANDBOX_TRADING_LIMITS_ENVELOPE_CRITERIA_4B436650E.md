    # 4B.4.3.6.6.50E — Paper Sandbox Trading Limits Envelope Criteria

    Decision: `PAPER_SANDBOX_CONTROLLED_PAPER_TRADING_SOAK_AUTHORIZATION_TRADING_LIMITS_ENVELOPE_CRITERIA_READY_REVIEW_AND_CONTRACT_ONLY_PAPER_SUBMIT_NOT_ENABLED_BY_PATCH_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.50D (4B436650D)`

    Next: `4B.4.3.6.6.50F — Paper Sandbox Kill-Switch Mandatory Preflight Criteria`

    ## Safety rules
    - 4B.4.3.6.6.50D (4B436650D) READY source is required
- 4B.4.3.6.6.50E is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.50F is not auto-unlocked by 4B.4.3.6.6.50E
