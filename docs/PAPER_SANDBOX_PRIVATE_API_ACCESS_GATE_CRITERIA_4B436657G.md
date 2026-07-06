    # 4B.4.3.6.6.57G — Private API Access Gate Criteria

    Decision: `LIVE_CREDENTIAL_ISOLATION_AUDIT_PRIVATE_API_ACCESS_GATE_CRITERIA_READY_LIVE_READINESS_REVIEW_ONLY_PRIVATE_API_ACCESS_NOT_ALLOWED_LIVE_REAL_NOT_APPROVED_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.57F (4B436657F)`

    Next: `4B.4.3.6.6.57H — Live Credential Isolation Audit Decision Gate`

    ## Safety rules
    - 4B.4.3.6.6.57F (4B436657F) READY source is required
- 4B.4.3.6.6.57G is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.57H is not auto-unlocked by 4B.4.3.6.6.57G
