# 4B.4.3.6.6.26D-H1 — Operator Cockpit V2 — Windows Safe PID Liveness Probe / Deterministic Single-Instance Lock Hotfix

## Scope

This overlay hotfix repairs Windows single-instance PID liveness probing in the local desktop wrapper.

## Repairs

- Keeps the current-process fast path and avoids any operating-system probe for the current PID.
- Uses WinAPI `OpenProcess`, `WaitForSingleObject`, optional `GetExitCodeProcess`, and `CloseHandle` on Windows.
- Does not call `os.kill(pid, 0)` on Windows.
- Preserves the POSIX signal-zero probe on POSIX systems.
- Adds a random `lock_id` owner token to newly acquired lock files.
- Releases a lock file only when its owner token still matches the current desktop wrapper instance.
- Preserves stale-lock recovery for old lock files that do not yet contain a token.
- Fails closed on unknown Windows probe failures to avoid opening a duplicate desktop cockpit.

## Safety contract

- No config mutation.
- No scheduler mutation.
- No trading action.
- No paper-mode enable.
- No live-mode enable.
- No model reload.
- No external network bind.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436626D_H1_operator_cockpit_v2_windows_safe_pid_liveness_probe_deterministic_single_instance_lock_hotfix_patch.zip" `
  -DestinationPath . `
  -Force
python tools/apply_4B436626D_H1_operator_cockpit_v2_windows_safe_pid_lock_hotfix.py
```
