# 4B.4.3.6.6.27D — Interval-Aware Training Candle Budget / Historical Range Accuracy Hardening

## Scope

This overlay replaces the legacy one-minute-only historical candle formula with a fail-closed interval-aware budget contract.

## Budget examples

| interval | candles / day | 30-day budget |
|---|---:|---:|
| 1m | 1440 | 43200 |
| 15m | 96 | 2880 |
| 1h | 24 | 720 |
| 4h | 6 | 180 |
| 1d | 1 | 30 |

## Safety

- No training is performed by the patch installer or checker.
- No model reload occurs.
- No scheduler configuration is changed.
- No trading action is performed.
- Unsupported intervals fail closed before any network request.

## Binance interval contract

The router accepts Binance Spot fixed-width kline intervals only: `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, and `1w`.

`1M` is deliberately blocked because month length is variable and cannot be represented as a fixed candle budget without an explicit calendar-range contract.
