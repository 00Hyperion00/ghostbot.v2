# 4B.4.3.6.6.23 Live-demo Acceptance Metrics / Performance Review

Generated at UTC: `2026-05-03T20:06:26Z`
Decision: **PASS**
Observation-only: `True`
No POST actions: `True`

## Acceptance Criteria

- Minimum samples: `10`
- Minimum pass rate: `100.0`%
- Max WS disconnects: `2`
- Max log errors: `0`

## Blockers

- None

## Observations

- LOG_FILE_NOT_FOUND

## Selected Soak Report

- Path: `reports\4B436622_live_demo_soak_20260503_221507.json`
- Decision: `PASS`
- Samples: `31`
- Pass rate: `100.0`%
- Warnings: `0`
- Failures: `0`
- State counts: `{'FLAT': 31}`
- Signal counts: `{'HOLD': 31}`
- Reason counts: `{}`

## Runtime Status Snapshot

- Provided: `False`
- State: `None`
- WS: `None`
- Last signal: `None`
- Last signal confidence: `None`
- Config: `None`
- Model quality: `None`
- Performance: `None`

## Log Metrics

- Provided: `True`
- Lines: `None`
- Warnings: `None`
- Errors: `None`
- WS disconnects: `None`
- Strategy eval count: `None`
- Auto-trade skip count: `None`
- Order event count: `None`
- Signals: `None`
- Actions: `None`
- Skip codes: `None`
- Reason codes: `None`

## Risk Manager Notes

- PASS means the supervised live-demo soak evidence is acceptable for metrics review; it is not permission to arm real live trading.
- HOLD / AUTO_TRADE_SKIP with low-confidence reason codes is acceptable and preferred when decision margin is weak.
- WS reconnect observations are acceptable within the configured threshold only if health/status samples remain PASS.

## Next Phase

4B.4.3.6.6.24 — Pre-live risk gate / real trading arming checklist.
