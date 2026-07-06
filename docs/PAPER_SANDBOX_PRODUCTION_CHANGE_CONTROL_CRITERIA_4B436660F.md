    # 4B.4.3.6.6.60F — Production Change Control Criteria

    Decision: `PRE_LIVE_GOVERNANCE_PRODUCTION_CHANGE_CONTROL_CRITERIA_READY_GOVERNANCE_CLOSURE_ONLY_NO_AUTO_NEXT_PHASE_LIVE_REAL_NOT_APPROVED_EXCHANGE_SUBMIT_LOCKED`

    Source: `4B.4.3.6.6.60E (4B436660E)`

    Next: `4B.4.3.6.6.60G — Post Closure Operator Audit Criteria`

    ## Safety rules
    - 4B.4.3.6.6.60E (4B436660E) READY source is required
- 4B.4.3.6.6.60F is review/contract/gate only
- patch must not start runtime
- patch must not call localhost health endpoint
- patch must not collect runtime metrics
- patch must not enable paper submit
- patch must not perform paper submit
- patch must not perform network order submit
- patch must not approve live-real
- patch must not enable exchange-submit
- patch must not access private API
- 4B.4.3.6.6.60G is not auto-unlocked by 4B.4.3.6.6.60F
