# 4B.4.3.6.6.37D — Strict Config Unknown-Key Fail-Closed

This patch closes only `P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED` by adding a strict YAML schema guard and producing evidence that:

1. valid minimal config is accepted;
2. unknown root YAML keys raise `ConfigSchemaError`;
3. unknown nested YAML keys raise `ConfigSchemaError`;
4. no runtime config reload or runtime loader binding is performed;
5. paper/live/submit remain blocked.

Expected READY decision:

`STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_3_LOCKED`
