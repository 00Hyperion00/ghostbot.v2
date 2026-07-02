let latestSnapshot = null;
let pendingConfirm = null;
let cockpitWs = null;
let reconnectTimer = null;
let latestSecurityPolicy = null;
let latestDisableDecision = { ok: false, reason: 'BOOTSTRAP_PENDING', message: 'Cockpit bootstrap bekleniyor.' };

const AUTH_TOKEN_KEY = 'tradebot.cockpit.authToken';
const OPERATOR_KEY = 'tradebot.cockpit.operatorId';
const SECURITY_BOOTSTRAP_HOTFIX_VERSION = '4B.4.3.6.6.33C-H1';
const UX_HEALTH_OBSERVABILITY_VERSION = '4B.4.3.6.6.33D';
const ACTION_AUDIT_RUNTIME_LOCK_VERSION = '4B.4.3.6.6.33E';
const RISK_RECONCILIATION_VERSION = '4B.4.3.6.6.33F';
const RECONCILIATION_EXECUTION_VERSION = '4B.4.3.6.6.33G';
const RECONCILIATION_DECISION_APPLY_VERSION = '4B.4.3.6.6.33H';
const ENGINE_POSITION_RECOVERY_GATE_VERSION = '4B.4.3.6.6.33I';
const CONNECTION_STATES = Object.freeze({
  BOOTSTRAP: 'BOOTSTRAP',
  AUTH_BLOCKED: 'AUTH_BLOCKED',
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  DISCONNECTED: 'DISCONNECTED',
  WS_AUTH_REJECTED: 'WS_AUTH_REJECTED',
  API_ERROR: 'API_ERROR',
});
let latestRuntimeLock = {};
let latestEntryGuard = {};
let latestActionAuditSummary = {};
let connectionState = {
  state: CONNECTION_STATES.BOOTSTRAP,
  reason: 'INITIAL_LOAD',
  since: Date.now(),
  wsRetryBlocked: false,
  lastHttpStatus: null,
  lastWsCloseCode: null,
};

function byId(id) { return document.getElementById(id); }
function text(id, value) { const el = byId(id); if (el) el.textContent = value ?? '-'; }
function fmt(value, digits = 4) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return Number.isFinite(value) ? value.toFixed(digits) : '-';
  return String(value);
}
function fmtSec(value) {
  if (value === null || value === undefined || value === '') return '-';
  const sec = Number(value);
  if (!Number.isFinite(sec)) return '-';
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const min = Math.floor(sec / 60);
  const rem = Math.floor(sec % 60);
  return `${min}m ${rem}s`;
}
function fmtMs(value) {
  if (value === null || value === undefined || value === '') return '-';
  const ms = Number(value);
  if (!Number.isFinite(ms)) return '-';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
function loadSecurityInputs() {
  const operator = localStorage.getItem(OPERATOR_KEY) || 'operator-local';
  const token = localStorage.getItem(AUTH_TOKEN_KEY) || '';
  const op = byId('operatorInput');
  const tk = byId('authTokenInput');
  if (op) op.value = operator;
  if (tk) tk.value = token;
}
function saveSecurityInputs() {
  const op = (byId('operatorInput')?.value || '').trim() || 'operator-local';
  const tk = (byId('authTokenInput')?.value || '').trim();
  localStorage.setItem(OPERATOR_KEY, op);
  localStorage.setItem(AUTH_TOKEN_KEY, tk);
  byId('actionResult').textContent = 'Security headers saved locally. Reconnecting cockpit...';
  if (cockpitWs) {
    try { cockpitWs.close(); } catch (_) {}
    cockpitWs = null;
  }
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  setConnectionState(CONNECTION_STATES.BOOTSTRAP, 'SECURITY_INPUTS_SAVED');
  setTimeout(bootstrapCockpit, 250);
}
function authHeaders({ includeOperator = true, includeAuth = true } = {}) {
  const headers = {};
  const token = localStorage.getItem(AUTH_TOKEN_KEY) || '';
  const operator = localStorage.getItem(OPERATOR_KEY) || '';
  if (includeAuth && token) headers['X-TradeBot-Auth'] = token;
  if (includeOperator && operator) headers['X-TradeBot-Operator'] = operator;
  return headers;
}
function localTokenPresent() {
  return !!String(localStorage.getItem(AUTH_TOKEN_KEY) || '').trim();
}
function localOperatorPresent() {
  return !!String(localStorage.getItem(OPERATOR_KEY) || '').trim();
}
function setConnectionState(state, reason, extra = {}) {
  connectionState = {
    ...connectionState,
    ...extra,
    state,
    reason: reason || state,
    since: Date.now(),
  };
  const online = state === CONNECTION_STATES.CONNECTED;
  const label = online ? 'CONNECTED' : state;
  const el = byId('connection');
  if (el) {
    el.textContent = label;
    el.classList.toggle('online', online);
  }
  renderConnectionStateMachine();
}
function renderConnectionStateMachine() {
  const ageSec = Math.max((Date.now() - connectionState.since) / 1000, 0);
  kv('connectionStateBox', {
    'State': connectionState.state,
    'Reason': connectionState.reason,
    'State Age': fmtSec(ageSec),
    'WS Retry Blocked': connectionState.wsRetryBlocked,
    'Last HTTP': connectionState.lastHttpStatus ?? '-',
    'Last WS Close': connectionState.lastWsCloseCode ?? '-',
  });
}
function setProtectedButtonsEnabled(enabled, reason = 'SECURITY_READY') {
  latestDisableDecision = enabled
    ? { ok: true, reason: 'SECURITY_READY', message: 'Protected actions enabled.' }
    : { ok: false, reason, message: reason };
  applyProtectedButtonGuards(enabled, reason);
  renderProtectedActionDisableReasons(latestDisableDecision);
}
function protectedActionButtons() {
  return Array.from(document.querySelectorAll('button')).filter((button) => {
    const onclick = button.getAttribute('onclick') || '';
    return button.dataset.protectedAction || onclick.includes('postOperatorAction') || onclick.includes('postDanger');
  });
}
function applyProtectedButtonGuards(enabled = latestDisableDecision.ok, reason = latestDisableDecision.reason) {
  protectedActionButtons().forEach((button) => {
    button.disabled = !enabled;
    button.title = enabled ? '' : `Protected action disabled: ${reason}`;
  });
  if (enabled) {
    const entryDisabled = !!latestEntryGuard.force_buy_disabled;
    document.querySelectorAll('[data-entry-action="true"]').forEach((button) => {
      button.disabled = entryDisabled;
      button.title = entryDisabled ? `Entry disabled: ${latestEntryGuard.disable_reason || 'ENTRY_GUARD_ACTIVE'}` : '';
    });
    document.querySelectorAll('[data-runtime-lock-action="clear-stale"]').forEach((button) => {
      const available = !!latestRuntimeLock.stale_reclaim_safe;
      button.disabled = !available;
      button.title = available ? 'Clear stale runtime lock with typed confirmation.' : 'No safe stale runtime lock reclaim is available.';
    });
  }
}
function renderProtectedActionDisableReasons(decision = latestDisableDecision) {
  kv('protectedActionBox', {
    'Enabled': !!decision.ok,
    'Reason': decision.reason || '-',
    'Operator Present': localOperatorPresent(),
    'Token Present In UI': localTokenPresent(),
    'Message': decision.message || '-',
  });
}
function setSecurityPill(security) {
  const el = byId('securityPill');
  if (!el) return;
  const required = !!(security || {}).auth_required;
  const configured = !!(security || {}).auth_configured || !!(security || {}).token_configured;
  const failClosed = !!(security || {}).fail_closed_no_token;
  el.classList.remove('ok', 'fail');
  if (failClosed) {
    el.textContent = 'SECURITY: FAIL-CLOSED';
    el.classList.add('fail');
  } else if (required && configured) {
    el.textContent = 'SECURITY: AUTH ON';
    el.classList.add('ok');
  } else if (required) {
    el.textContent = 'SECURITY: TOKEN REQUIRED';
    el.classList.add('fail');
  } else {
    el.textContent = 'SECURITY: LOCAL DRY-RUN';
  }
}
function securityAllowsProtectedCalls(security = latestSecurityPolicy) {
  security = security || {};
  const authRequired = !!security.auth_required;
  const tokenConfigured = !!(security.auth_configured || security.token_configured);
  const failClosed = !!security.fail_closed_no_token;
  if (failClosed) {
    return {
      ok: false,
      reason: 'AUTH_REQUIRED_BUT_NO_TOKEN_CONFIGURED',
      message: [
        'Cockpit fail-closed: runtime auth istiyor ama server tarafında token tanımlı değil.',
        'PowerShell örneği:',
        '$env:TRADEBOT_COCKPIT_AUTH_TOKEN="uzun-rastgele-token"',
        'tradebot cockpit --config config.local.yaml',
        'Sonra UI içindeki Auth Token alanına aynı tokenı yazıp Save yap.'
      ].join('\n')
    };
  }
  if (authRequired && tokenConfigured && !localTokenPresent()) {
    return {
      ok: false,
      reason: 'AUTH_TOKEN_REQUIRED_IN_UI',
      message: 'Cockpit auth aktif. UI içindeki Auth Token alanına configured tokenı yazıp Save yap. WebSocket ve protected API çağrıları token girilene kadar başlatılmaz.'
    };
  }
  if (authRequired && !localOperatorPresent()) {
    return {
      ok: false,
      reason: 'OPERATOR_ID_REQUIRED_IN_UI',
      message: 'Operator identity zorunlu. Operator alanına net bir operatör kimliği yazıp Save yap.'
    };
  }
  return { ok: true, reason: 'SECURITY_READY', message: 'Security bootstrap ready.' };
}
function renderSecurityBlocking(decision) {
  setConnectionState(CONNECTION_STATES.AUTH_BLOCKED, decision.reason, { wsRetryBlocked: true });
  setProtectedButtonsEnabled(false, decision.reason);
  byId('actionResult').textContent = `${decision.reason}\n${decision.message}`;
  text('runtimeRiskTitle', 'Cockpit security bootstrap required');
  text('runtimeRiskMessage', decision.message);
  text('runtimeRiskReason', decision.reason);
  text('runtimeRiskAction', 'Configure token / save UI security headers');
  const banner = byId('runtimeRiskBanner');
  setRiskClass(banner, 'RED', 'risk-banner');
}
function kv(containerId, data) {
  const box = byId(containerId);
  if (!box) return;
  box.innerHTML = '';
  Object.entries(data).forEach(([key, value]) => {
    const row = document.createElement('div');
    row.innerHTML = `<span>${key}</span><strong>${value ?? '-'}</strong>`;
    box.appendChild(row);
  });
}
function setRiskClass(el, badge, prefix) {
  if (!el) return;
  el.classList.remove(`${prefix}-green`, `${prefix}-yellow`, `${prefix}-red`, `${prefix}-unknown`, 'green', 'yellow', 'red');
  const normalized = String(badge || 'UNKNOWN').toLowerCase();
  if (['green', 'yellow', 'red'].includes(normalized)) {
    el.classList.add(`${prefix}-${normalized}`);
    if (prefix === 'risk-banner') el.classList.add(normalized);
  } else {
    el.classList.add(`${prefix}-unknown`);
  }
}
function renderRuntimeAwareness(awareness) {
  awareness = awareness || {};
  const badge = String(awareness.risk_badge || 'UNKNOWN').toUpperCase();
  const badgeEl = byId('runtimeRiskBadge');
  if (badgeEl) badgeEl.textContent = `RISK: ${badge}`;
  setRiskClass(badgeEl, badge, 'risk');
  const banner = byId('runtimeRiskBanner');
  setRiskClass(banner, badge, 'risk-banner');
  text('runtimeRiskTitle', awareness.banner_title || 'Runtime inventory tracking');
  text('runtimeRiskMessage', awareness.banner_message || '-');
  text('runtimeRiskReason', (awareness.reason_codes || []).join(', ') || '-');
  text('runtimeRiskAction', awareness.recommended_action || '-');
  kv('awarenessBox', {
    'Risk Badge': badge,
    'Base Asset': awareness.base_asset || '-',
    'Tradable Base': fmt(awareness.tradable_base),
    'Position Present': awareness.position_present,
    'Pending Present': awareness.pending_present,
    'Base Not Tracked': awareness.base_balance_present_position_not_tracked,
    'Orphan Recovery': awareness.orphan_local_position_recovery_detected,
    'Action Required': awareness.auto_entry_risk_attention_required
  });
}
function renderLogs(logs) {
  const box = byId('logs');
  if (!box) return;
  box.innerHTML = '';
  (logs || []).slice(0, 120).forEach(item => {
    const line = document.createElement('div');
    const level = String(item.level || 'INFO').toUpperCase();
    line.className = `log-line log-${level}`;
    const ts = item.ts ? new Date(item.ts).toLocaleString() : '-';
    line.textContent = `${ts} | ${level.padEnd(5)} | ${(item.code || '-').padEnd(28)} | ${item.message || '-'} | ${JSON.stringify(item.data || {})}`;
    box.appendChild(line);
  });
}
function renderOperatorActions(actions) {
  const box = byId('operatorActions');
  if (!box) return;
  box.innerHTML = '';
  (actions || []).slice(0, 80).forEach(item => {
    const line = document.createElement('div');
    const outcome = String(item.outcome || '-');
    const ts = item.ts ? new Date(item.ts).toLocaleString() : '-';
    line.className = `operator-action-line outcome-${outcome}`;
    line.textContent = `${ts} | ${String(item.actor || '-').padEnd(18)} | ${String(item.action || '-').padEnd(28)} | ${outcome}`;
    box.appendChild(line);
  });
}
function renderAuthStatusCard(security, requestSecurity) {
  security = security || {};
  requestSecurity = requestSecurity || {};
  kv('authStatusBox', {
    'Auth Required': !!security.auth_required,
    'Server Token Configured': !!(security.auth_configured || security.token_configured),
    'Fail Closed': !!security.fail_closed_no_token,
    'Request Authenticated': !!requestSecurity.authenticated,
    'Operator': requestSecurity.operator_id || localStorage.getItem(OPERATOR_KEY) || '-',
    'Auth Header': requestSecurity.auth_header || security.auth_header || 'X-TradeBot-Auth',
    'Health Exception': !!security.read_only_health_exception,
  });
}
function renderSystemHealth(system) {
  system = system || {};
  const heartbeatAge = Number(system.heartbeat_age_ms || 0);
  const heartbeatLabel = fmtMs(heartbeatAge);
  text('heartbeat', heartbeatLabel);
  const heartbeatEl = byId('heartbeat');
  if (heartbeatEl) {
    heartbeatEl.classList.remove('heartbeat-ok', 'heartbeat-warn', 'heartbeat-stale');
    heartbeatEl.classList.add(heartbeatAge > 5000 ? 'heartbeat-stale' : heartbeatAge > 2500 ? 'heartbeat-warn' : 'heartbeat-ok');
  }
  kv('systemBox', {
    'PID': system.pid || '-',
    'Process Uptime': fmtSec(system.uptime_sec),
    'Engine Running': !!system.engine_running,
    'Engine Uptime': fmtSec(system.engine_uptime_sec),
    'Heartbeat Age': heartbeatLabel,
    'CPU %': system.cpu_percent === null || system.cpu_percent === undefined ? 'psutil unavailable' : fmt(system.cpu_percent, 2),
    'RAM RSS MB': system.memory_rss_mb === null || system.memory_rss_mb === undefined ? 'psutil unavailable' : fmt(system.memory_rss_mb, 2),
    'RAM %': system.memory_percent === null || system.memory_percent === undefined ? 'psutil unavailable' : fmt(system.memory_percent, 4),
    'psutil': !!system.psutil_available,
  });
}
function renderRuntimeLock(lock) {
  latestRuntimeLock = lock || {};
  kv('runtimeLockBox', {
    'Exists': !!latestRuntimeLock.exists,
    'Held By Current': !!latestRuntimeLock.held_by_current_process,
    'Duplicate Blocked': !!latestRuntimeLock.duplicate_instance_blocked,
    'PID': latestRuntimeLock.pid ?? '-',
    'PID Alive': latestRuntimeLock.pid_alive ?? '-',
    'Age': fmtSec(latestRuntimeLock.age_seconds),
    'Stale By Age': !!latestRuntimeLock.stale_by_age,
    'Stale Dead PID': !!latestRuntimeLock.stale_by_dead_pid,
    'Clear Available': !!latestRuntimeLock.stale_reclaim_safe,
    'Path': latestRuntimeLock.path || '-',
    'Reasons': (latestRuntimeLock.reason_codes || []).join(', ') || '-'
  });
}
function renderEntryGuard(guard) {
  latestEntryGuard = guard || {};
  kv('entryGuardBox', {
    'Entry Actions Enabled': !!latestEntryGuard.entry_actions_enabled,
    'Force BUY Disabled': !!latestEntryGuard.force_buy_disabled,
    'Risk Badge': latestEntryGuard.risk_badge || '-',
    'Disable Reason': latestEntryGuard.disable_reason || '-',
    'Message': latestEntryGuard.message || '-',
    'Version': latestEntryGuard.contract_version || ACTION_AUDIT_RUNTIME_LOCK_VERSION
  });
  applyProtectedButtonGuards(latestDisableDecision.ok, latestDisableDecision.reason);
}
function renderBalanceReview(snapshot) {
  const review = snapshot.balance_review || snapshot.runtime_awareness?.balance_review || {};
  const target = byId('balanceReview');
  if (!target) return;
  target.textContent = JSON.stringify(review, null, 2);
}
function renderRiskReconciliation(snapshot) {
  const rec = snapshot.risk_reconciliation || snapshot.runtime_awareness?.risk_reconciliation || {};
  const target = byId('riskReconciliationCard');
  if (!target) return;
  const blocked = !!rec.entry_blocked_until_reconciled;
  target.classList.toggle('reconciliation-blocked', blocked);
  target.classList.toggle('reconciliation-ok', !blocked);
  target.innerHTML = `
    <div>Status</div><strong>${rec.status || '-'}</strong>
    <div>Review required</div><strong>${fmtBool(rec.review_required)}</strong>
    <div>Reconciled</div><strong>${fmtBool(rec.reconciled)}</strong>
    <div>Entry blocked</div><strong>${fmtBool(rec.entry_blocked_until_reconciled)}</strong>
    <div>Acknowledgement</div><strong>${fmtBool(rec.acknowledgement_present)}</strong>
    <div>Reason codes</div><strong>${(rec.reason_codes || []).join(', ') || '-'}</strong>
    <div>Recommended action</div><strong>${rec.recommended_action || '-'}</strong>
  `;
}
function renderActionAuditSummary(summary) {
  latestActionAuditSummary = summary || {};
  kv('actionAuditSummaryBox', {
    'Returned': latestActionAuditSummary.total_returned ?? 0,
    'Latest TS': latestActionAuditSummary.latest_ts ? new Date(latestActionAuditSummary.latest_ts).toLocaleString() : '-',
    'Blocked': !!latestActionAuditSummary.has_blocked_actions,
    'Failed': !!latestActionAuditSummary.has_failed_actions,
    'By Outcome': JSON.stringify(latestActionAuditSummary.by_outcome || {}),
    'By Action': JSON.stringify(latestActionAuditSummary.by_action || {})
  });
}
function renderSnapshot(payload) {
  latestSnapshot = payload;
  const status = payload.status || {};
  const position = status.position_snapshot || {};
  const perf = status.performance_snapshot || {};
  const risk = status.risk_snapshot || {};
  const system = payload.system || {};
  const awareness = payload.runtime_awareness || {};
  const runtimeLock = payload.runtime_lock || {};
  const entryGuard = payload.entry_guard || {};
  const actionAuditSummary = payload.operator_action_ledger || {};
  const security = payload.security || latestSecurityPolicy || {};
  latestSecurityPolicy = security;

  text('contract', `Contract: ${payload.contract_version || '-'} / Hardening: ${payload.runtime_hardening_version || '-'} / Security: ${payload.security_gate_version || '-'} / UX: ${payload.ux_health_version || system.ux_health_version || '-'}`);
  text('state', status.state || '-');
  text('ws', status.ws_status || '-');
  text('symbol', status.symbol || '-');
  text('signal', (status.decision_audit_snapshot || {}).effective_decision?.signal || status.current_signal || '-');
  text('signalReason', (status.decision_audit_snapshot || {}).effective_decision?.reason || status.signal_reason || '-');
  text('position', position.present ? 'OPEN' : 'FLAT');
  text('qty', fmt(position.qty));
  text('pnl', fmt(position.unrealized_pnl ?? perf.realized_pnl));

  setSecurityPill(security);
  renderAuthStatusCard(security, payload.request_security || {});
  renderRuntimeAwareness(awareness);
  renderRuntimeLock(runtimeLock);
  renderEntryGuard(entryGuard);
  renderActionAuditSummary(actionAuditSummary);
  renderSystemHealth(system);
  renderLogs(payload.logs || []);
  renderOperatorActions(payload.operator_actions || []);
  renderProtectedActionDisableReasons(latestDisableDecision);
  renderConnectionStateMachine();
  renderReconciliationExecution(payload);
  renderReconciliationDecisionApply(payload);
  renderEnginePositionRecoveryGate(payload);

  kv('securityBox', {
    'Auth Required': security.auth_required,
    'Auth Configured': security.auth_configured || security.token_configured,
    'Fail Closed': security.fail_closed_no_token,
    'Local Only': security.local_only_required,
    'Danger Confirmations': security.danger_confirmations_enabled,
    'Operator Header': security.operator_header || 'X-TradeBot-Operator'
  });
  kv('riskBox', {
    'Safe Mode': risk.safe_mode,
    'Kill Switch': risk.kill_switch_active,
    'Daily Loss %': fmt(risk.daily_loss_pct),
    'Consecutive Losses': risk.consecutive_losses,
    'Max Daily Trades': risk.max_daily_trades,
    'Trades Today': risk.trades_today
  });
  kv('contractBox', {
    '33A Foundation': payload.contract_version,
    '33B Runtime Hardening': payload.runtime_hardening_version,
    '33C Security Gate': payload.security_gate_version,
    '33C-H1 Auth Bootstrap': SECURITY_BOOTSTRAP_HOTFIX_VERSION,
    '33D UX Health': payload.ux_health_version || system.ux_health_version,
    '33E Action Audit Lock': payload.action_audit_runtime_lock_version || system.action_audit_runtime_lock_version || ACTION_AUDIT_RUNTIME_LOCK_VERSION,
    '33I Engine Recovery Gate': payload.engine_position_recovery_gate_version || ENGINE_POSITION_RECOVERY_GATE_VERSION,
    'Runtime Lock': (payload.cockpit || {}).runtime_lock_present,
    'Startup Error': (payload.cockpit || {}).startup_error || '-'
  });
}
async function requestHealthPolicy() {
  try {
    const res = await fetch('/api/cockpit/health');
    const payload = await res.json();
    latestSecurityPolicy = payload.security || {};
    setSecurityPill(latestSecurityPolicy);
    renderAuthStatusCard(latestSecurityPolicy, {});
    text('contract', `Security: ${payload.security_gate_version || '-'} / UX: ${payload.ux_health_version || UX_HEALTH_OBSERVABILITY_VERSION}`);
    setConnectionState(CONNECTION_STATES.BOOTSTRAP, 'HEALTH_OK', { lastHttpStatus: res.status });
    return latestSecurityPolicy;
  } catch (exc) {
    setConnectionState(CONNECTION_STATES.API_ERROR, 'HEALTH_FETCH_FAILED', { lastHttpStatus: 'ERR' });
    byId('actionResult').textContent = `Health check failed: ${exc}`;
    return null;
  }
}
function connectWs() {
  const decision = securityAllowsProtectedCalls();
  if (!decision.ok) {
    renderSecurityBlocking(decision);
    return;
  }
  if (cockpitWs && [WebSocket.OPEN, WebSocket.CONNECTING].includes(cockpitWs.readyState)) return;
  const token = encodeURIComponent(localStorage.getItem(AUTH_TOKEN_KEY) || '');
  const operator = encodeURIComponent(localStorage.getItem(OPERATOR_KEY) || '');
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  setConnectionState(CONNECTION_STATES.CONNECTING, 'WS_CONNECTING', { wsRetryBlocked: false });
  cockpitWs = new WebSocket(`${proto}://${location.host}/ws/cockpit?token=${token}&operator=${operator}`);
  cockpitWs.onopen = () => {
    setConnectionState(CONNECTION_STATES.CONNECTED, 'WS_OPEN', { lastWsCloseCode: null, wsRetryBlocked: false });
    setProtectedButtonsEnabled(true);
  };
  cockpitWs.onclose = (event) => {
    setProtectedButtonsEnabled(false, event.code === 1008 ? 'WEBSOCKET_AUTH_REJECTED' : 'WEBSOCKET_DISCONNECTED');
    if (event.code === 1008) {
      setConnectionState(CONNECTION_STATES.WS_AUTH_REJECTED, 'WEBSOCKET_AUTH_REJECTED', { lastWsCloseCode: event.code, wsRetryBlocked: true });
      byId('actionResult').textContent = 'WebSocket auth rejected. Token ve Operator alanlarını kontrol edip Save yap.';
      return;
    }
    setConnectionState(CONNECTION_STATES.DISCONNECTED, 'WS_CLOSED', { lastWsCloseCode: event.code, wsRetryBlocked: false });
    const retryDecision = securityAllowsProtectedCalls();
    if (!retryDecision.ok) {
      renderSecurityBlocking(retryDecision);
      return;
    }
    reconnectTimer = setTimeout(connectWs, 1500);
  };
  cockpitWs.onerror = () => setConnectionState(CONNECTION_STATES.API_ERROR, 'WS_ERROR');
  cockpitWs.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'snapshot') renderSnapshot(msg.payload);
  };
}
async function fetchSnapshot() {
  const decision = securityAllowsProtectedCalls();
  if (!decision.ok) {
    renderSecurityBlocking(decision);
    return;
  }
  try {
    const res = await fetch('/api/cockpit/snapshot', { headers: authHeaders() });
    const payload = await res.json();
    if (!res.ok) {
      setConnectionState(res.status === 401 || res.status === 403 || res.status === 503 ? CONNECTION_STATES.AUTH_BLOCKED : CONNECTION_STATES.API_ERROR, 'SNAPSHOT_FETCH_FAILED', { lastHttpStatus: res.status });
      setProtectedButtonsEnabled(false, `SNAPSHOT_HTTP_${res.status}`);
      byId('actionResult').textContent = JSON.stringify(payload, null, 2);
      return;
    }
    setProtectedButtonsEnabled(true);
    renderSnapshot(payload);
  } catch (exc) {
    setConnectionState(CONNECTION_STATES.API_ERROR, 'SNAPSHOT_EXCEPTION', { lastHttpStatus: 'ERR' });
    byId('actionResult').textContent = String(exc);
  }
}
function requestConfirmModal(expected) {
  return new Promise((resolve) => {
    pendingConfirm = { expected, resolve };
    text('confirmModalText', `Bu aksiyon için şu metni aynen yaz: ${expected}`);
    const input = byId('confirmModalInput');
    input.value = '';
    byId('confirmModal').classList.remove('hidden');
    setTimeout(() => input.focus(), 30);
  });
}
function cancelConfirmModal() {
  byId('confirmModal').classList.add('hidden');
  if (pendingConfirm) pendingConfirm.resolve(null);
  pendingConfirm = null;
}
function acceptConfirmModal() {
  const value = byId('confirmModalInput').value;
  byId('confirmModal').classList.add('hidden');
  if (pendingConfirm) pendingConfirm.resolve(value);
  pendingConfirm = null;
}
async function postOperatorAction(path, extraHeaders = {}) {
  const decision = securityAllowsProtectedCalls();
  if (!decision.ok) {
    renderSecurityBlocking(decision);
    return { ok: false, reason_code: decision.reason };
  }
  const res = await fetch(path, { method: 'POST', headers: { ...authHeaders(), ...extraHeaders } });
  const payload = await res.json().catch(() => ({ ok: false, error: 'non-json response' }));
  byId('actionResult').textContent = JSON.stringify(payload, null, 2);
  setTimeout(fetchSnapshot, 250);
  return payload;
}
async function postDanger(path, expected) {
  const decision = securityAllowsProtectedCalls();
  if (!decision.ok) {
    renderSecurityBlocking(decision);
    return;
  }
  const supplied = await requestConfirmModal(expected);
  if (supplied !== expected) {
    byId('actionResult').textContent = 'Confirmation mismatch. Action cancelled.';
    return;
  }
  return postOperatorAction(path, { 'X-TradeBot-Confirm': expected });
}
async function bootstrapCockpit() {
  setProtectedButtonsEnabled(false, 'BOOTSTRAP_PENDING');
  loadSecurityInputs();
  renderConnectionStateMachine();
  renderProtectedActionDisableReasons();
  const security = await requestHealthPolicy();
  if (!security) return;
  const decision = securityAllowsProtectedCalls(security);
  if (!decision.ok) {
    renderSecurityBlocking(decision);
    return;
  }
  setProtectedButtonsEnabled(true);
  connectWs();
  await fetchSnapshot();
}
setInterval(renderConnectionStateMachine, 1000);
bootstrapCockpit();

const ackRiskBtn = byId('ackRiskReconciliationBtn');
if (ackRiskBtn) { ackRiskBtn.onclick = () => postDanger('/api/cockpit/risk-reconciliation/acknowledge', 'CONFIRM_ACKNOWLEDGE_POSITION_NOT_TRACKED'); }
const clearRiskAckBtn = byId('clearRiskAckBtn');
if (clearRiskAckBtn) { clearRiskAckBtn.onclick = () => postDanger('/api/cockpit/risk-reconciliation/clear-acknowledgement', 'CONFIRM_CLEAR_RECONCILIATION_ACKNOWLEDGEMENT'); }


function renderReconciliationExecution(snapshot) {
  const execution = snapshot?.reconciliation_execution || snapshot?.runtime_awareness?.reconciliation_execution || {};
  const candidate = snapshot?.tracked_position_adoption_candidate || snapshot?.runtime_awareness?.tracked_position_adoption_candidate || {};
  text('reconciliationExecutionBox', JSON.stringify({
    version: RECONCILIATION_EXECUTION_VERSION,
    reconciliation_clear: execution.reconciliation_clear,
    entry_guard_release_authorized: execution.entry_guard_release_authorized,
    dust_safe_eligible: execution.dust_safe_eligible,
    decision_type: execution.decision_type,
    candidate_available: candidate.candidate_available,
    candidate_qty: candidate.candidate_qty,
    reason_codes: execution.reason_codes || [],
  }, null, 2));
}

async function confirmBalanceSnapshot() {
  await postDanger('/api/cockpit/risk-reconciliation/confirm-balance-snapshot', 'CONFIRM_BALANCE_SNAPSHOT_REVIEWED');
}

async function resolveDustSafeBaseBalance() {
  await postDanger('/api/cockpit/risk-reconciliation/resolve-dust-safe-base-balance', 'CONFIRM_RESOLVE_DUST_SAFE_BASE_BALANCE');
}

async function adoptPositionCandidate() {
  await postDanger('/api/cockpit/risk-reconciliation/adopt-position-candidate', 'CONFIRM_ADOPT_TRACKED_POSITION_CANDIDATE');
}


function renderReconciliationDecisionApply(snapshot) {
  const apply = snapshot?.reconciliation_decision_apply || snapshot?.runtime_awareness?.reconciliation_decision_apply || {};
  const resolver = snapshot?.runtime_lock_owner_mismatch_resolver || snapshot?.runtime_awareness?.runtime_lock_owner_mismatch_resolver || {};
  text('reconciliationDecisionApplyBox', JSON.stringify({
    version: RECONCILIATION_DECISION_APPLY_VERSION,
    apply_status: apply.apply_status,
    decision_type: apply.decision_type,
    entry_guard_release_verified: apply.entry_guard_release_verified,
    engine_position_state_mutated: apply.engine_position_state_mutated,
    reason_codes: apply.reason_codes || [],
  }, null, 2));
  text('runtimeLockResolverBox', JSON.stringify({
    owner_mismatch_detected: resolver.owner_mismatch_detected,
    lock_pid: resolver.lock_pid,
    lock_pid_alive: resolver.lock_pid_alive,
    safe_clear_allowed: resolver.safe_clear_allowed,
    restart_required: resolver.restart_required,
    reason_codes: resolver.reason_codes || [],
  }, null, 2));
}

async function applyTrackedPositionCandidateReview() {
  await postDanger('/api/cockpit/risk-reconciliation/apply-tracked-position-candidate-review', 'CONFIRM_APPLY_TRACKED_POSITION_CANDIDATE_REVIEW');
}

async function applyDustSafeClear() {
  await postDanger('/api/cockpit/risk-reconciliation/apply-dust-safe-clear', 'CONFIRM_APPLY_DUST_SAFE_CLEAR');
}

async function clearManualReconciliationDecision() {
  await postDanger('/api/cockpit/risk-reconciliation/clear-manual-decision', 'CONFIRM_CLEAR_RECONCILIATION_DECISION');
}

async function resolveRuntimeLockOwnerMismatch() {
  await postDanger('/api/cockpit/runtime-lock/resolve-owner-mismatch', 'CONFIRM_RESOLVE_RUNTIME_LOCK_OWNER_MISMATCH');
}


function renderEnginePositionRecoveryGate(snapshot) {
  const gate = snapshot?.engine_position_recovery_gate || snapshot?.runtime_awareness?.engine_position_recovery_gate || {};
  text('enginePositionRecoveryGateBox', JSON.stringify({
    version: ENGINE_POSITION_RECOVERY_GATE_VERSION,
    status: gate.status,
    reviewed_candidate_present: gate.reviewed_candidate_present,
    plan_present: gate.plan_present,
    plan_confirmed: gate.plan_confirmed,
    engine_position_state_mutated: gate.engine_position_state_mutated,
    external_recovery_verified: gate.external_recovery_verified,
    entry_guard_release_verified: gate.entry_guard_release_verified,
    requires_manual_external_recovery: gate.requires_manual_external_recovery,
    reason_codes: gate.reason_codes || [],
  }, null, 2));
}

async function createEnginePositionRecoveryPlan() {
  await postDanger('/api/cockpit/engine-position-recovery/create-plan', 'CONFIRM_CREATE_ENGINE_POSITION_RECOVERY_PLAN');
}

async function confirmEnginePositionRecoveryPlan() {
  await postDanger('/api/cockpit/engine-position-recovery/confirm-plan', 'CONFIRM_CONFIRM_ENGINE_POSITION_RECOVERY_PLAN');
}

async function verifyEnginePositionRecoveryCompletion() {
  await postDanger('/api/cockpit/engine-position-recovery/verify-completion', 'CONFIRM_VERIFY_ENGINE_POSITION_RECOVERY_COMPLETE');
}

async function clearEnginePositionRecoveryPlan() {
  await postDanger('/api/cockpit/engine-position-recovery/clear-plan', 'CONFIRM_CLEAR_ENGINE_POSITION_RECOVERY_PLAN');
}


document.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const action = target.dataset?.action;
  if (!action) return;
  const handlers = {
    'confirm-balance-snapshot': confirmBalanceSnapshot,
    'resolve-dust-safe-base-balance': resolveDustSafeBaseBalance,
    'adopt-position-candidate': adoptPositionCandidate,
    'apply-tracked-position-candidate-review': applyTrackedPositionCandidateReview,
    'apply-dust-safe-clear': applyDustSafeClear,
    'clear-manual-reconciliation-decision': clearManualReconciliationDecision,
    'resolve-runtime-lock-owner-mismatch': resolveRuntimeLockOwnerMismatch,
    'create-engine-position-recovery-plan': createEnginePositionRecoveryPlan,
    'confirm-engine-position-recovery-plan': confirmEnginePositionRecoveryPlan,
    'verify-engine-position-recovery-completion': verifyEnginePositionRecoveryCompletion,
    'clear-engine-position-recovery-plan': clearEnginePositionRecoveryPlan,
  };
  const handler = handlers[action];
  if (handler) handler();
});
