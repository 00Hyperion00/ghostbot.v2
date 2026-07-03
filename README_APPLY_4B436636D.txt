4B.4.3.6.6.36D — Public Observation Execution Authorization

This patch is authorization-ledger only and fail-closed.
It validates 36C READY dry-run collector evidence, then emits:
- Operator Observation Token ledger/template
- Network-Off Safety Override Ledger
- No-Submit Execution Seal

It does not validate a real operator token, does not unlock authorization, does not perform network/HTTP requests, public market-data collection, runtime evidence collection, runtime probes, private API reads, paper/live activation, or exchange/order submit.
