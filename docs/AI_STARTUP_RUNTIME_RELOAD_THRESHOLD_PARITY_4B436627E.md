# 4B.4.3.6.6.27E — AI Startup / Runtime Reload Threshold Parity

This overlay eliminates silent AI decision drift between initial startup and runtime model reload.

## Contract

The same immutable threshold contract is used by engine startup, runtime reload, standalone AI service startup and standalone service reload:

- threshold
- buy_threshold
- sell_threshold
- hold_band_low
- hold_band_high
- indecision_margin
- threshold_profile

Runtime reload may replace the model path but may not silently mutate thresholds. Any requested override must match the startup contract exactly or reload is blocked with `MODEL_THRESHOLD_STARTUP_RELOAD_MISMATCH`.

## Safety

- No training is started.
- No model reload is performed during patch apply or checker execution.
- No config mutation is performed.
- No scheduler mutation is performed.
- No paper/live/order enablement is performed.
