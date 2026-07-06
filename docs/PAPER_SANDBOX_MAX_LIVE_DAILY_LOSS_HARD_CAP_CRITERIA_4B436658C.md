    # 4B.4.3.6.6.58C — Max Live Daily Loss Hard Cap Criteria

    Decision: `LIVE_RISK_LIMIT_CIRCUIT_BREAKER_MAX_LIVE_DAILY_LOSS_HARD_CAP_CRITERIA_READY_LIVE_READINESS_REVIEW_ONLY_PRIVATE_API_ACCESS_NOT_ALLOWED_LIVE_REAL_NOT_APPROVED_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.58B (4B436658B)`

    Next: `4B.4.3.6.6.58D — Max Live Position Count Criteria`

    ## Safety rules
    - 4B.4.3.6.6.58B (4B436658B) READY source is required
- 4B.4.3.6.6.58C is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.58D is not auto-unlocked by 4B.4.3.6.6.58C
