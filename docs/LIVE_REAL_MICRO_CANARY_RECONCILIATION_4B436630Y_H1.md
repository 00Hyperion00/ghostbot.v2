# 4B.4.3.6.6.30Y-H1 Live-Real Micro Canary Reconciliation Hotfix

This hotfix allows a bounded manual minimum-notional quantity adjustment during 30Y reconciliation.

Risk rules:

- The patch still performs no Binance submit.
- Additional live-real submit remains blocked.
- Emergency stop and kill switch must be armed.
- The adjustment must be explicitly requested with operator reason.
- Fill notional must remain within 30X micro-canary total notional cap.
- Fill/account/ledger reconciliation must still match the real execution evidence.

The observed Binance order `8114595899` filled `0.0029 ETH` at `1713.36`, total `4.968744 USDT`. This differs from the 30X request quantity but remains within the intended micro-canary notional envelope; H1 records that as an explicit manual min-notional adjustment rather than silently accepting a quantity mismatch.
