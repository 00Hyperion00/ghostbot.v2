4B.4.3.6.6.36F — Public Observation Evidence Closure

This patch is interim-closure only and fail-closed.
It validates 36E READY, audits local 36A-36E tags, locks network-off evidence digests, and emits a no-submit Phase-36 interim closure.

It does not unlock 36G, execute network/HTTP requests, collect public market data, write observation artifacts, run probes, read private API/account data, enable paper/live, or submit orders.
