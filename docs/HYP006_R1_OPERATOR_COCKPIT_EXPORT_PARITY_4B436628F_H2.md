# 4B.4.3.6.6.28F-H2 Operator Cockpit HYP-006 Export Source Parity

This hotfix moves read-only Operator Cockpit safe export sources from legacy HYP-005 artifacts to HYP-006-R1 dashboard/acceptance/ledger artifacts.

Scope:

- latest logger export -> `reports/hyp006_r1_canonical/4B436628D_hyp006_r1_shadow_observation_logger_*.json`
- latest collection export -> `reports/hyp006_r1_canonical/4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json`
- latest audit export -> `reports/hyp006_r1_canonical/4B436628F_hyp006_r1_operator_cockpit_baseline_*.json`
- latest ledger export -> `reports/hyp006_r1_canonical/4B436628D_hyp006_r1_shadow_ledger_*.jsonl`

Risk contract:

- read-only only
- no config mutation
- no scheduler mutation
- no training
- no reload
- no trading action
- no paper/live/order enablement
