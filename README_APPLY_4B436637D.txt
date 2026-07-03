4B.4.3.6.6.37D Strict Config Unknown-Key Fail-Closed

Purpose
- Close P0-3: P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED.
- Add a strict YAML config schema guard module.
- Prove root and nested unknown YAML keys fail closed with ConfigSchemaError.
- Keep Phase 37 planning-only and no-submit.

Apply
```powershell
python tools/apply_4B436637D_strict_config_unknown_key_fail_closed.py
```

Check
```powershell
$env:PYTHONPATH="src"
python tools/check_4B436637D_strict_config_unknown_key_fail_closed.py --once-json
```

Run
```powershell
$env:PYTHONPATH="src"
python tools/run_4B436637D_strict_config_unknown_key_fail_closed.py --reports-dir .eportsecovery --once-json
```

Safety
- No runtime config reload.
- No runtime loader binding in this phase.
- No network, submit, paper/live enable, runtime overlay, training, reload.
- No report cleanup, move, delete, archive, deduplication.
