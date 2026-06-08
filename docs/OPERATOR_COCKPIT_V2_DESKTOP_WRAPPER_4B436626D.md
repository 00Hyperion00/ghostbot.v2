# 4B.4.3.6.6.26D — Operator Cockpit V2 — Desktop Wrapper / Single-Launch Local Application Shell

## Scope

This overlay adds a desktop application shell around the existing local read-only Operator Cockpit V2.

## Runtime model

- Starts the existing local cockpit server automatically.
- Binds only to loopback (`127.0.0.1`, `localhost`, or `::1`).
- Opens the cockpit in an embedded `pywebview` desktop window.
- Stops the local server when the desktop window closes.
- Prevents duplicate desktop instances with a stale-aware temp-directory PID lock.
- Fails safely when the configured port is already occupied.
- Offers browser fallback only when the operator explicitly supplies `--allow-browser-fallback`.

## Security contract

- No config mutation.
- No scheduler mutation.
- No trading action.
- No paper-mode enable.
- No live-mode enable.
- No model reload.
- No external network bind.

## Dependency

The embedded desktop window uses `pywebview`. Install it explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_operator_cockpit_v2_desktop_dependency_4B436626D.ps1
```

## Start

```powershell
powershell -ExecutionPolicy Bypass -File tools\start_operator_cockpit_v2_desktop_4B436626D.ps1
```

For a double-click launcher, use:

```text
tools\start_operator_cockpit_v2_desktop_4B436626D.cmd
```

## Optional desktop shortcut

Shortcut creation is intentionally explicit and is not performed during patch application:

```powershell
powershell -ExecutionPolicy Bypass -File tools\create_operator_cockpit_v2_desktop_shortcut_4B436626D.ps1
```

## Headless smoke check

```powershell
python tools/run_operator_cockpit_v2_desktop_4B436626D.py --project-root . --host 127.0.0.1 --port 0 --headless-smoke-json
```
