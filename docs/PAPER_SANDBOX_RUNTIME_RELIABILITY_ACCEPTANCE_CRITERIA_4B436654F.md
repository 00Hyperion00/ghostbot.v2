    # 4B.4.3.6.6.54F — Paper Sandbox Runtime Reliability Acceptance Criteria

    Decision: `PAPER_SANDBOX_CONTROLLED_PAPER_TRADING_SOAK_ACCEPTANCE_RUNTIME_RELIABILITY_ACCEPTANCE_CRITERIA_READY_EVIDENCE_AND_ACCEPTANCE_REVIEW_ONLY_PAPER_TRADING_NOT_ACCEPTED_BY_PATCH_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.54E (4B436654E)`

    Next: `4B.4.3.6.6.54G — Paper Sandbox Operator Runbook Acceptance Criteria`

    ## Safety rules
    - 4B.4.3.6.6.54E (4B436654E) READY source is required
- 4B.4.3.6.6.54F is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.54G is not auto-unlocked by 4B.4.3.6.6.54F
