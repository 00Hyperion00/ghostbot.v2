    # 4B.4.3.6.6.57D — IP Allowlist Criteria

    Decision: `LIVE_CREDENTIAL_ISOLATION_AUDIT_IP_ALLOWLIST_CRITERIA_READY_LIVE_READINESS_REVIEW_ONLY_PRIVATE_API_ACCESS_NOT_ALLOWED_LIVE_REAL_NOT_APPROVED_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.57C (4B436657C)`

    Next: `4B.4.3.6.6.57E — Secret Rotation Criteria`

    ## Safety rules
    - 4B.4.3.6.6.57C (4B436657C) READY source is required
- 4B.4.3.6.6.57D is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.57E is not auto-unlocked by 4B.4.3.6.6.57D
