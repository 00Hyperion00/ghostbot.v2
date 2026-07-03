4B.4.3.6.6.36E — Public Observation Network-Off Execution Package

This patch is no-network and fail-closed.
It validates 36D READY authorization, then emits:
- Token Presence Audit
- No-Network Collector Simulation
- Observation Execution Dry-Run Evidence Seal

It does not consume operator tokens, unlock authorization, perform network/HTTP requests, fetch public market data, write observation artifacts, run runtime probes, read private API/account state, activate paper/live, or submit orders.
