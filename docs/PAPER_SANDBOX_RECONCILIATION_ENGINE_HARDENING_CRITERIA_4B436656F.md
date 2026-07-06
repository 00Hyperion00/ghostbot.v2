    # 4B.4.3.6.6.56F — Reconciliation Engine Hardening Criteria

    Decision: `P0_PRODUCTION_HARDENING_RECONCILIATION_ENGINE_HARDENING_CRITERIA_READY_READINESS_AND_HARDENING_REVIEW_ONLY_LIVE_REAL_NOT_APPROVED_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.56E (4B436656E)`

    Next: `4B.4.3.6.6.56G — Monitoring Alerting Hardening Criteria`

    ## Safety rules
    - 4B.4.3.6.6.56E (4B436656E) READY source is required
- 4B.4.3.6.6.56F is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.56G is not auto-unlocked by 4B.4.3.6.6.56F
