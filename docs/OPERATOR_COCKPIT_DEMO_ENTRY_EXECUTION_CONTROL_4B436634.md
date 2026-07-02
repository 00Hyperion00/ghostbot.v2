# 4B.4.3.6.6.34 — Demo Entry Execution Controlled Re-Enablement

This patch builds on 33M and introduces a demo-only controlled entry execution gate.

## Added

- Entry Action Dry-Run
- Min Notional & Step Size Verification
- Order Intent Audit
- Demo-Only Trade Enablement
- Post-Entry Protective Exit Verification
- `trade.force_buy` is now additionally blocked by the 34 demo entry gate unless a fresh dry-run, filter verification, intent audit, and time-limited demo-only authorization are present.

## Safety Contract

- Demo-only runtime is required: `market_type=spot_demo`, `execution_mode=live_demo`, `base_url=demo-api.binance.com`.
- No live-real enablement.
- No auth relaxation.
- No engine position mutation by the gate itself.
- No order path mutation except explicitly operator-confirmed existing `trade.force_buy` after 34 gate authorization.
- Post-entry protective exit verification is read-only and must be explicitly recorded after demo entry.

## Runtime Flow

1. Confirm 33M final state is green and entry actions are available.
2. Run 34 dry-run.
3. Verify min-notional and step-size.
4. Record order intent audit.
5. Authorize demo-only entry for a short TTL.
6. Trigger existing `trade.force_buy` with `CONFIRM_FORCE_BUY`.
7. Verify post-entry protective exit.

## Test

```powershell
python tools/compile_operator_cockpit_4B436634.py
pytest tests/test_operator_cockpit_4B436634.py
python -m compileall -q src	radebot\cockpit src	radebot\cli.py
```
