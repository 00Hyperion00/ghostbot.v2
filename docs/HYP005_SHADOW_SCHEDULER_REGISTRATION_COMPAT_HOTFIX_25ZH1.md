# 4B.4.3.6.6.25Z-H1 HYP-005 Shadow Scheduler Registration Compatibility Hotfix

This hotfix fixes a Windows PowerShell compatibility issue in the generated scheduler registration helper.
Some ScheduledTasks module builds reject `-DisallowStartIfOnBatteries` on `New-ScheduledTaskSettingsSet`.

## Fixes

- Avoids unsupported battery parameters during `New-ScheduledTaskSettingsSet` construction.
- Sets optional battery-related properties only when the returned settings object exposes them.
- Fixes no-order cycle script project-root resolution when the scheduler pack is generated under `reports/<pack_dir>`.

## Safety

Paper/live remain blocked. This hotfix does not train, reload, mutate config, start paper trading, enable live trading, or send orders.
