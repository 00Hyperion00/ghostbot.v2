# 4B.4.3.6.6.29C SQLite Audit Ledger Upgrade

Amaç: KV/log MVP persistence üzerine audit-grade baseline tablolarını eklemek.

Kapsam:
- `schema_migrations`
- `orders`
- `fills`
- `positions`
- `risk_events`
- `model_decisions`
- `balance_snapshots`
- `operator_actions`
- schema version `2`
- append helper methodları

Bu patch order path, runtime overlay, paper/live/live-real veya HYP-006 thresholdlarını açmaz.
