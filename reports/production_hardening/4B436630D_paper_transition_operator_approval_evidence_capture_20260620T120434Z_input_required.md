# 4B.4.3.6.6.30D Operator Approval Evidence Capture

This report captures typed operator approval evidence, a TTL-bound approval snapshot, sandbox runtime envelope freeze evidence, and final paper risk-cap verification evidence. It does not enable paper orders or live-real.

## Decision
- `decision`: `PAPER_TRANSITION_APPROVAL_EVIDENCE_CAPTURE_INPUT_REQUIRED_LIVE_REAL_BLOCKED`
- `read_only`: `True`
- `approved_for_operator_approval_evidence_capture`: `False`
- `approved_for_paper_transition_candidate_review`: `False`
- `approved_for_paper_transition_candidate`: `False`
- `approved_for_paper_candidate`: `False`
- `approved_for_live_real`: `False`
- `paper_order_enablement_still_blocked`: `True`
- `trading_action_performed`: `False`

## Evidence gates
- `typed_approval_evidence_verified`: `False`
- `ttl_bound_approval_snapshot_verified`: `False`
- `runtime_envelope_freeze_token_verified`: `False`
- `final_risk_cap_verification_evidence_verified`: `False`
- `source_30b_ready`: `False`
- `source_30c_review_ready`: `False`

## Reason codes
- `TYPED_OPERATOR_APPROVAL_NOT_ISSUED`
- `TYPED_OPERATOR_ID_MISSING`
- `TYPED_OPERATOR_APPROVAL_TOKEN_MISMATCH`
- `TYPED_APPROVAL_ISSUED_AT_MISSING`
- `RUNTIME_ENVELOPE_NOT_FROZEN`
- `RUNTIME_ENVELOPE_FREEZE_TOKEN_MISMATCH`
- `FINAL_RISK_CAP_NOT_VERIFIED_BY_OPERATOR`
- `SOURCE_30B_READY_OPERATOR_APPROVAL_EVIDENCE_REQUIRED`
- `SOURCE_30C_READY_REVIEW_EVIDENCE_REQUIRED`
- `PAPER_ORDER_ENABLEMENT_STILL_BLOCKED`
- `LIVE_REAL_HARD_BLOCK_VERIFIED`
