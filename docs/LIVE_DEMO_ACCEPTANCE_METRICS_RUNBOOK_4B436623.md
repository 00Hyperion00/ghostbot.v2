# 4B.4.3.6.6.23 Live-demo Acceptance Metrics / Performance Review

## Purpose

Convert the 4B.4.3.6.6.22 supervised soak evidence into an acceptance metrics report.
This phase is observation-only and must not modify trading behavior.

## Required preconditions

- 4B.4.3.6.6.21 release acceptance report is PASS.
- 4B.4.3.6.6.22 live-demo supervised soak has at least one uninterrupted PASS report.
- API is running only if `--base-url` runtime snapshot is requested.

## Apply and test

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python tools/apply_4B436623_live_demo_acceptance_metrics.py
python -m pytest -q tests/test_live_demo_acceptance_metrics_4B436623.py
```

## Generate metrics from existing soak reports

```powershell
python tools/generate_live_demo_acceptance_metrics_4B436623.py
```

## Generate metrics with live `/status` snapshot

```powershell
python tools/generate_live_demo_acceptance_metrics_4B436623.py --base-url http://127.0.0.1:8000
```

## Generate metrics with API log parsing

```powershell
python tools/generate_live_demo_acceptance_metrics_4B436623.py --log-file ".\logs\tradebot.log"
```

If the live log is not in `logs\tradebot.log`, pass the correct text log path.

## Acceptance criteria

Default PASS criteria:

- Selected 4B436622 soak report decision is PASS.
- At least 10 samples.
- Pass rate is 100%.
- No soak failures.
- No operator interruption.
- Observation-only contract is present.
- Real live trading is not armed.
- Log error count is 0 if a log file is provided.
- WS disconnect count is not greater than 2 if a log file is provided.

## Risk note

PASS in this phase does not authorize real live trading. It only confirms that live-demo observation metrics are acceptable for the next risk gate.

## Next phase

4B.4.3.6.6.24 — Pre-live risk gate / real trading arming checklist.
