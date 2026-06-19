# 4B.4.3.6.6.28G-H8 HYP-006 BNBUSDT Overlay OOS Evaluation

This patch adds a no-order decision pack for the BNBUSDT primary overlay measurement.

It compares the latest H7 BNBUSDT measurement against the previous H7 measurement and produces an out-of-sample delta report. It is intentionally fail-closed:

- no runtime overlay activation
- no parameter relaxation
- no paper/live enablement
- no order action
- no training or reload
- no scheduler mutation

Primary output:

- `reports/hyp006_r1_canonical/4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_*.json`
- `reports/hyp006_r1_canonical/4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_*.md`

The report may approve `approved_for_bnbusdt_oos_evaluation` and `approved_for_oos_monitoring_continuation`, but it never approves runtime activation, parameter relaxation, paper/live, or order execution.
