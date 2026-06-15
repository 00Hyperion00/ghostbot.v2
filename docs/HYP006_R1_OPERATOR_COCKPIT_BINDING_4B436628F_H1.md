# 4B.4.3.6.6.28F-H1 Operator Cockpit HYP-006 Binding Hotfix

Bu hotfix Operator Cockpit V2 read-only snapshot üretiminde HYP-006-R1 dashboard seed ve 28G continuity delta evidence verisini aktif research branch olarak bağlar.

## Amaç

- HYP-005-R1 legacy model/strategy panelinin aktif branch gibi görünmesini bastırmak.
- HYP-006-R1 branch_id, namespace, scheduler health, acceptance tracking ve no-order continuity metriklerini Operator Cockpit snapshot içine taşımak.
- Paper/live/training/reload/order kapılarını kapalı tutmak.

## Güvenlik kontratı

- Config mutation yok.
- Scheduler mutation yok.
- Task creation yok.
- Training/reload yok.
- Trading/order yok.
- HTTP mutasyon endpointleri read-only kalır.

## Veri kaynağı önceliği

1. `reports/hyp006_r1_canonical/4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json`
2. `reports/hyp006_r1_canonical/4B436628F_hyp006_r1_operator_cockpit_baseline_*.json`
3. `reports/hyp006_r1_canonical/4B436628E_hyp006_r1_scheduler_execution_health_verify_*.json`
4. `reports/hyp006_r1_canonical/4B436628D_hyp006_r1_shadow_ledger_*.jsonl`

Bu kaynaklar yoksa cockpit fail-closed şekilde legacy snapshot'a geri döner; hiçbir işlem açılmaz.
