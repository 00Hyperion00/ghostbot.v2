# 4B.4.3.6.6.37J — Report Commit Policy

This patch closes P0-9 by adding a no-submit evidence-governance contract:

- canonical evidence selection under `reports/recovery`
- commit whitelist for patch files and 37J canonical reports
- report provenance guard with required source/digest/status fields
- deny-by-default behavior for noncanonical reports and runtime/local artifacts

The patch intentionally does not run git operations. Operator review remains mandatory before manual commit/tag.

Safety invariants:

- no report delete/move/dedup/archive
- no patch backup cleanup
- no paper/live/exchange submit
- no network/http/signed request
- no runtime start/overlay/reload/training
- no next-phase auto unlock
