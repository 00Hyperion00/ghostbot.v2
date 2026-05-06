# 4B.4.3.6.6.21 Operator Acceptance Runbook

## Purpose

This runbook freezes the 4B.4.3.6.6.21 release candidate and gives the operator a repeatable acceptance path before moving to supervised live-demo soak testing.

## Required Starting Point

- Stable backup exists after 4B.4.3.6.6.20t11.
- 4B.4.3.6.6.21a acceptance runner installed.
- 4B.4.3.6.6.21b runtime smoke and dashboard contract checker installed.
- 4B.4.3.6.6.21c legacy patch scanner/archive completed.

## Acceptance Commands

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python -m compileall -q src tests tools
python tools/run_4B436621_acceptance_tests.py
python tools/check_dashboard_contract_4B436621.py
```

Start the API in a separate PowerShell and keep it open:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
$env:PYTHONPATH="$PWD\src"
python -m tradebot.cli api --config config.local.yaml --host 127.0.0.1 --port 8000
```

Run runtime smoke in another PowerShell:

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2
python tools/run_runtime_smoke_4B436621.py --base-url http://127.0.0.1:8000
```

Generate the final report:

```powershell
python tools/generate_4B436621_release_acceptance.py
```

## PASS Criteria

- Acceptance gate is PASS.
- Dashboard contract checker is PASS.
- Runtime smoke is PASS.
- Legacy high-risk scripts are archived or explicitly reviewed.
- No syntax/import errors exist.
- No critical config warning exists before supervised live-demo soak.

## Stop Conditions

- Any acceptance group fails.
- Runtime smoke cannot reach `/health` or `/status`.
- Dashboard contract checker fails.
- Archived dashboard patch scripts are accidentally restored to active `tools` flow.
- Config indicates real live trading is armed outside a dedicated live pilot phase.

## Next Phase

4B.4.3.6.6.22 — Live-demo supervised soak test.
