# 4B.4.3.6.6.27F — Risk-Percent Position Sizing / Quote-Balance Boundaries / Fail-Closed Quantity Contract Hardening

This overlay replaces the entry-side fixed notional arithmetic with an auditable position sizing contract.

## Entry modes

- `fixed_quote`: preserves the configured `order_notional_usd` behavior.
- `risk_percent_quote_balance`: derives quote budget from usable free quote balance.
- `risk_percent`: accepted only as a legacy alias and normalized to `risk_percent_quote_balance`.

## Boundaries

The entry budget is bounded by free quote balance after reserve, optional `max_quote_budget_usd`, Binance `LOT_SIZE`, `minQty`, `maxQty`, and buffered `minNotional`.

Risk-reducing exit quantity logic is deliberately untouched. Exits continue to use the existing position/base-asset path.

## Safety

- No config file mutation.
- No scheduler mutation.
- No training or reload.
- No paper/live enablement.
- No network request.
- No order action.
