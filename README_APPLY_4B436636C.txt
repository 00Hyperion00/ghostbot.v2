4B.4.3.6.6.36C — Public Observation Dry-Run Collector

This patch is dry-run collector planning code and fail-closed by default.
It validates 36B READY preflight, then emits:
- Read-Only Public Data Fetch Adapter
- Observation Artifact Writer
- No-Submit Runtime Evidence Guard

It does not perform network/HTTP requests, public market data collection, runtime evidence collection, runtime probes, private API reads, paper/live activation, or exchange/order submit.
