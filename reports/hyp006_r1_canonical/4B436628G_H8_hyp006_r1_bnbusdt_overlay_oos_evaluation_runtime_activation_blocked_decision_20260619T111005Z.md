# 4B.4.3.6.6.28G-H8 HYP-006 BNBUSDT Overlay OOS Evaluation

This decision pack compares the latest BNBUSDT no-order overlay measurement with the previous H7 measurement. It blocks runtime activation and all trading gates.

## Decision

- `decision`: `HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED`
- `read_only`: `True`
- `no_order_oos_evaluation_only`: `True`
- `approved_for_bnbusdt_oos_evaluation`: `True`
- `approved_for_oos_monitoring_continuation`: `True`
- `approved_for_runtime_overlay_activation_candidate`: `False`
- `approved_for_runtime_overlay_activation`: `False`
- `approved_for_parameter_relaxation_candidate`: `False`
- `approved_for_paper_candidate`: `False`
- `approved_for_live_real`: `False`
- `runtime_overlay_activation_performed`: `False`
- `training_performed`: `False`
- `reload_performed`: `False`
- `trading_action_performed`: `False`
- `order_actions_performed`: `False`

## Latest measurement

- `symbol`: `BNBUSDT`
- `event_count`: `13`
- `matured_count`: `13`
- `win_rate_pct`: `76.923077`
- `mean_return_bps`: `126.61364`
- `median_return_bps`: `142.929363`
- `profit_factor`: `5.432608`
- `worst_return_bps`: `-312.205541`
- `worst_mae_bps`: `-426.691375`
- `net_return_bps`: `1645.977319`

## OOS delta

- `event_count_delta`: `1`
- `matured_count_delta`: `1`
- `win_rate_pct_delta`: `1.923077`
- `mean_return_bps_delta`: `21.51453`
- `median_return_bps_delta`: `25.658806`
- `profit_factor_delta`: `1.036232`
- `worst_return_bps_delta`: `0.0`
- `worst_mae_bps_delta`: `0.0`
- `net_return_bps_delta`: `384.787993`

## Guards

- `oos_guard_pass`: `True`
- `oos_guard_reasons`: `[]`
- `tail_risk_monitoring_required`: `True`
- `tail_risk_reasons`: `WORST_MAE_MONITORING_REQUIRED`

## Recommendation

Continue BNBUSDT no-order OOS monitoring only. Runtime overlay activation remains blocked; parameter, paper/live, and order gates remain closed.
