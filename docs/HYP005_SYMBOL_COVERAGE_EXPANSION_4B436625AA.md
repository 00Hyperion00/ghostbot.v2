# 4B.4.3.6.6.25AA — HYP-005 Controlled Symbol Coverage Expansion Gate

Purpose: expand HYP-005 no-order shadow collection from 4 symbols to exactly 10 controlled symbols.

Approved 10-symbol set:

```text
BTCUSDT
ETHUSDT
SOLUSDT
BNBUSDT
XRPUSDT
DOGEUSDT
ADAUSDT
AVAXUSDT
LINKUSDT
LTCUSDT
```

Safety scope:

```text
No training.
No model reload.
No paper trading.
No live trading.
No order actions.
No POST requests.
```

The gate writes a report and, when requested, a config file:

```text
reports/4B436625AA_hyp005_symbol_coverage_expansion_*.json
reports/4B436625AA_hyp005_symbol_coverage_expansion_*.md
config/hyp005_shadow_symbols_4B436625AA.json
config/hyp005_shadow_symbols_4B436625AA.yaml
```

The resulting symbol list can then be passed to the existing 25Z scheduler pack generator:

```powershell
python tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py `
  --reports-dir reports `
  --include-all `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,LINKUSDT,LTCUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

After reviewing the generated scheduler pack, manually register the new task helper from the latest 25Z pack directory.

Paper/live remain blocked until future acceptance gates pass.
