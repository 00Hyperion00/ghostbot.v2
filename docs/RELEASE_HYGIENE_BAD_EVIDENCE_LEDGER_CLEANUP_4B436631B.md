# 4B.4.3.6.6.31B Release Hygiene & Bad Evidence Ledger Cleanup

Purpose: close the live micro-canary audit trail after accepted `31A-H3` by recording the bad `31A / 31A-H1 / 31A-H2` NOT_READY history, moving remaining bad evidence files into a quarantine folder, and writing a final audit snapshot.

Risk boundary:

- No Binance order submission.
- No exchange API call.
- No scheduler mutation.
- No strategy parameter mutation.
- No runtime overlay activation.
- No additional live-real order approval.

Ready decision:

`RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY_FINAL_AUDIT_SNAPSHOT_NO_FURTHER_LIVE_ORDER`

Source requirement: latest or explicit accepted `31A-H3` READY JSON with no further live orders and `patch_network_submit_attempted=false`.
