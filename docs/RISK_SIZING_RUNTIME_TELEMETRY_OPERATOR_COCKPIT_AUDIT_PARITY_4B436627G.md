# 4B.4.3.6.6.27G — Risk-Sizing Runtime Telemetry / Operator Cockpit Audit Parity / Fail-Closed Evidence Export Gate

This patch is read-only. It does not mutate configuration, scheduler state, model state, or trading permissions.

It adds:

- read-only SQLite runtime sizing telemetry collection using `mode=ro`,
- operator cockpit snapshot audit parity for sizing and entry preflight events,
- a JSON telemetry view,
- an additive risk-sizing evidence ZIP endpoint,
- a fail-closed gate that rejects the dedicated evidence ZIP when required runtime evidence is absent,
- native desktop export bridge entries for the new JSON and ZIP endpoints.

The legacy operator-cockpit evidence pack remains unchanged for backward compatibility.
