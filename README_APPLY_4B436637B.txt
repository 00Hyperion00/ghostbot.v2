4B.4.3.6.6.37B — Install Contract Alignment

This patch is a no-submit Production Hardening P0-1 step.
It aligns requirements.txt to pyproject.toml [project].dependencies, adds a bounded README install-contract block, and normalizes known launcher pip install commands when those files exist.

It does not enable paper/live/live-real, runtime overlay, training, reload, network calls, exchange submit, order submit, public market data collection, destructive cleanup, archive moves, file deletes, or next-phase unlocks.
