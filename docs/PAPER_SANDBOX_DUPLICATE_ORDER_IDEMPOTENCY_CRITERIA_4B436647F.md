# 4B.4.3.6.6.47F — Paper Sandbox Duplicate Order Idempotency Criteria

Patch ID: `4B436647F`

Decision: `PAPER_SANDBOX_PAPER_ORDER_PATH_AUTHORIZATION_DUPLICATE_ORDER_IDEMPOTENCY_CRITERIA_READY_AUTHORIZATION_REVIEW_ONLY_ORDER_PATH_NOT_OPENED_BY_PATCH_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

Source: `4B.4.3.6.6.47E / 4B436647E`

Mode: `PHASE_47_DUPLICATE_ORDER_IDEMPOTENCY_CRITERIA_REVIEW_CONTRACT_ONLY_NO_ACTIVATION_BY_PATCH`

This phase is review/contract/gate only. It does not start runtime, call health endpoint, collect metrics, ingest actual evidence, accept soak evidence, open paper order path, enable paper submit, submit network orders, approve live-real, or enable exchange submit.
