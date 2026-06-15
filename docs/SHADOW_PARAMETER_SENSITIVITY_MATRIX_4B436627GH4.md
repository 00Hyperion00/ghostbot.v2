# 4B.4.3.6.6.27G-H4 — No-Order Parameter Sensitivity Matrix

This patch adds a read-only HYP-005-R1 threshold sensitivity report.

It evaluates a matrix of:

- `min_sweep_bps`,
- `min_wick_pct`,
- `max_compression_ratio`.

The output is research-only. It does not mutate canonical strategy parameters, scheduler configuration, model state, paper trading, live trading, or order execution permissions.

A variant marked as research-promising is not paper approval. It only means the variant deserves a separate out-of-sample validation gate.
