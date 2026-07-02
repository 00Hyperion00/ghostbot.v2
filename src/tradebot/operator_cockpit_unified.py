from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CONTRACT_VERSION = "4B.4.3.6.6.32B-H1"
COCKPIT_TITLE = "TradeBot V2 Operator Cockpit"
DEFAULT_REPORTS_DIR = Path("reports/production_hardening")
DEFAULT_SHADOW_DIR = Path("reports/hyp006_r1_canonical")

SAFE_FALSE_FIELDS = {
    "approved_for_live_real_order",
    "approved_for_second_micro_order",
    "patch_network_submit_attempted",
    "live_real_order_submit_performed",
    "exchange_submit_allowed",
    "network_submit_allowed",
}

@dataclass(frozen=True)
class PhaseReport:
    phase: str
    file_name: str = ""
    decision: str = "MISSING"
    verified: bool = False
    last_write_time: str = ""

@dataclass(frozen=True)
class RiskCaps:
    capital_cap_usdt: float | None = None
    second_micro_max_notional_usdt: float | None = None
    daily_loss_limit_usdt: float | None = None
    max_slippage_bps: float | None = None

@dataclass(frozen=True)
class SecondMicroCandidate:
    symbol: str = "ETHUSDT"
    side: str = "BUY"
    order_type: str = "MARKET"
    candidate_qty: float | None = None
    candidate_notional_usdt: float | None = None
    reference_price: float | None = None
    exchange_submit_allowed: bool = False
    network_submit_allowed: bool = False
    requires_32c: bool = True

@dataclass(frozen=True)
class ShadowHealth:
    active: bool = False
    latest_file: str = ""
    latest_ledger: str = ""
    latest_log_time: str = ""
    latest_shadow_count: int | None = None
    latest_new_unique_count: int | None = None
    mean_return_bps: float | None = None
    profit_factor: float | None = None
    log_tail: str = ""
    unsafe_hits: tuple[str, ...] = ()

@dataclass(frozen=True)
class CockpitSnapshot:
    contract_version: str
    generated_at_utc: str
    latest_accepted_phase: str
    live_micro_canary_state: str
    no_live_order_lock: bool
    approved_for_live_real_order: bool
    approved_for_second_micro_order: bool
    emergency_stop_armed: bool
    shadow_collection_active: bool
    phase_31b: PhaseReport
    phase_32a: PhaseReport
    phase_32b: PhaseReport
    risk_caps: RiskCaps
    second_micro_candidate: SecondMicroCandidate
    shadow_health: ShadowHealth
    status_endpoint_online: bool
    status_endpoint_payload: dict[str, Any] = field(default_factory=dict)
    operator_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def repo_root(start: Path | None = None) -> Path:
    cursor = (start or Path.cwd()).resolve()
    for candidate in (cursor, *cursor.parents):
        if (candidate / "src").exists() or (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return cursor


def _safe_load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {"value": value}


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_values(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)


def _deep_get(payload: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    wanted = set(keys)
    for item in _iter_values(payload):
        if isinstance(item, dict):
            for key in wanted:
                if key in item:
                    return item[key]
    return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "ready", "ok"}:
            return True
        if normalized in {"false", "0", "no", "n", "", "none", "null"}:
            return False
    return default


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def _latest_file(directory: Path, patterns: Iterable[str]) -> Path | None:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(p for p in directory.glob(pattern) if p.is_file() and "_not_ready" not in p.name)
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _phase_report(phase: str, path: Path | None, ready_marker: str) -> PhaseReport:
    if path is None:
        return PhaseReport(phase=phase)
    payload = _safe_load_json(path)
    decision = str(_deep_get(payload, ["decision", "status_decision"], "MISSING"))
    verified = ready_marker in decision and "NOT_READY" not in decision
    return PhaseReport(
        phase=phase,
        file_name=path.name,
        decision=decision,
        verified=verified,
        last_write_time=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
    )


def _read_status_endpoint(url: str = "http://127.0.0.1:8000/status", timeout: float = 0.6) -> tuple[bool, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310 - localhost operator status only.
            payload = json.loads(response.read().decode("utf-8"))
        return True, payload if isinstance(payload, dict) else {"value": payload}
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return False, {}


def _tail_text(path: Path, max_lines: int = 120) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return ""
    return "\n".join(lines[-max_lines:])


def _extract_shadow_metric(log_tail: str, key: str) -> str | None:
    pattern = re.compile(rf"-\s+{re.escape(key)}:\s+([^\r\n]+)")
    matches = pattern.findall(log_tail)
    return matches[-1].strip() if matches else None


def _shadow_health(root: Path) -> ShadowHealth:
    shadow_dir = root / DEFAULT_SHADOW_DIR
    log_path = shadow_dir / "hyp006_scheduler_stdout.log"
    log_tail = _tail_text(log_path, 120)
    latest_json = _latest_file(shadow_dir, ["4B436628D_hyp006_r1_shadow_observation_logger_*.json"])
    latest_ledger = _latest_file(shadow_dir, ["4B436628D_hyp006_r1_shadow_ledger_*.jsonl"])
    unsafe_terms = (
        "approved_for_live_real: True",
        "approved_for_paper_candidate: True",
        "order_submit",
        "exchange_submit",
        "live_submit",
    )
    unsafe_hits = tuple(term for term in unsafe_terms if term.lower() in log_tail.lower())
    latest_time = ""
    candidates = [p for p in (latest_json, latest_ledger, log_path if log_path.exists() else None) if p is not None]
    if candidates:
        latest_time = datetime.fromtimestamp(max(p.stat().st_mtime for p in candidates)).isoformat(timespec="seconds")
    return ShadowHealth(
        active=bool(latest_json or latest_ledger or log_tail) and not unsafe_hits,
        latest_file=latest_json.name if latest_json else "",
        latest_ledger=latest_ledger.name if latest_ledger else "",
        latest_log_time=latest_time,
        latest_shadow_count=_to_int(_extract_shadow_metric(log_tail, "shadow_observation_count")),
        latest_new_unique_count=_to_int(_extract_shadow_metric(log_tail, "new_unique_shadow_observation_count")),
        mean_return_bps=_to_float(_extract_shadow_metric(log_tail, "mean_return_bps")),
        profit_factor=_to_float(_extract_shadow_metric(log_tail, "profit_factor")),
        log_tail=log_tail,
        unsafe_hits=unsafe_hits,
    )


def build_cockpit_snapshot(root: Path | None = None, include_status_endpoint: bool = True) -> CockpitSnapshot:
    root = repo_root(root)
    reports = root / DEFAULT_REPORTS_DIR
    phase31b_file = _latest_file(reports, ["4B436631B_release_hygiene_bad_evidence_ledger_cleanup_*_ready.json"])
    phase32a_file = _latest_file(reports, ["4B436632A_post_freeze_release_candidate_review_*_ready.json"])
    phase32b_file = _latest_file(reports, ["4B436632B_second_micro_canary_submit_gate_*_ready.json"])

    phase31b_payload = _safe_load_json(phase31b_file) if phase31b_file else {}
    phase32a_payload = _safe_load_json(phase32a_file) if phase32a_file else {}
    phase32b_payload = _safe_load_json(phase32b_file) if phase32b_file else {}

    phase31b = _phase_report("4B.4.3.6.6.31B", phase31b_file, "RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY")
    phase32a = _phase_report("4B.4.3.6.6.32A", phase32a_file, "POST_FREEZE_RELEASE_CANDIDATE_REVIEW_READY")
    phase32b = _phase_report("4B.4.3.6.6.32B", phase32b_file, "SECOND_MICRO_CANARY_SUBMIT_GATE_READY")

    capital_cap = _to_float(_deep_get(phase32a_payload, ["capital_cap_usdt"], None))
    second_cap = _to_float(_deep_get(phase32a_payload, ["second_micro_max_notional_usdt"], None))
    daily_loss = _to_float(_deep_get(phase32a_payload, ["daily_loss_limit_usdt"], None))
    slippage = _to_float(_deep_get(phase32a_payload, ["max_slippage_bps"], None))
    reference_price = _to_float(_deep_get(phase32b_payload, ["reference_price", "reference_price_usdt"], None))
    candidate_qty = _to_float(_deep_get(phase32b_payload, ["candidate_qty", "candidate_quantity", "quantity"], None))
    candidate_notional = _to_float(_deep_get(phase32b_payload, ["estimated_notional", "estimated_notional_usdt", "candidate_notional_usdt"], None))

    emergency_stop_armed = _to_bool(
        _deep_get(phase32a_payload, ["emergency_stop_armed_verified", "emergency_stop_armed"], None),
        default=False,
    ) or _to_bool(_deep_get(phase32b_payload, ["emergency_stop_armed_verified", "emergency_stop_armed"], None), False)

    approved_for_live = _to_bool(
        _deep_get(phase32b_payload, ["approved_for_live_real_order", "approved_for_live_real", "live_real_order_approved"], False),
        default=False,
    )
    approved_for_second = _to_bool(
        _deep_get(phase32b_payload, ["approved_for_second_micro_order", "approved_for_second_micro_canary_order_submit"], False),
        default=False,
    )
    exchange_submit_allowed = _to_bool(_deep_get(phase32b_payload, ["exchange_submit_allowed", "approved_for_exchange_submit"], False), False)
    network_submit_allowed = _to_bool(_deep_get(phase32b_payload, ["network_submit_allowed", "patch_network_submit_allowed"], False), False)
    symbol = str(_deep_get(phase32b_payload, ["symbol"], "ETHUSDT"))
    side = str(_deep_get(phase32b_payload, ["side"], "BUY"))
    order_type = str(_deep_get(phase32b_payload, ["order_type"], "MARKET"))

    status_online, status_payload = _read_status_endpoint() if include_status_endpoint else (False, {})
    shadow = _shadow_health(root)
    no_live_order_lock = not approved_for_live and not approved_for_second and not exchange_submit_allowed and not network_submit_allowed
    latest_phase = "4B.4.3.6.6.32B" if phase32b.verified else "4B.4.3.6.6.32A" if phase32a.verified else "4B.4.3.6.6.31B" if phase31b.verified else "UNKNOWN"
    live_state = "SECOND_MICRO_CANDIDATE_ONLY" if phase32b.verified and no_live_order_lock else "FROZEN"
    operator_message = (
        "LIVE SUBMIT LOCKED — 32B only produced submit-request evidence. 32C is required for any real exchange submit."
        if no_live_order_lock
        else "WARNING — live submit flag detected. Review immediately."
    )

    return CockpitSnapshot(
        contract_version=CONTRACT_VERSION,
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        latest_accepted_phase=latest_phase,
        live_micro_canary_state=live_state,
        no_live_order_lock=no_live_order_lock,
        approved_for_live_real_order=approved_for_live,
        approved_for_second_micro_order=approved_for_second,
        emergency_stop_armed=emergency_stop_armed,
        shadow_collection_active=shadow.active,
        phase_31b=phase31b,
        phase_32a=phase32a,
        phase_32b=phase32b,
        risk_caps=RiskCaps(capital_cap, second_cap, daily_loss, slippage),
        second_micro_candidate=SecondMicroCandidate(
            symbol=symbol,
            side=side,
            order_type=order_type,
            candidate_qty=candidate_qty,
            candidate_notional_usdt=candidate_notional,
            reference_price=reference_price,
            exchange_submit_allowed=exchange_submit_allowed,
            network_submit_allowed=network_submit_allowed,
            requires_32c=True,
        ),
        shadow_health=shadow,
        status_endpoint_online=status_online,
        status_endpoint_payload=status_payload,
        operator_message=operator_message,
    )


def write_snapshot_report(root: Path | None = None, reports_dir: Path | None = None) -> Path:
    root = repo_root(root)
    snapshot = build_cockpit_snapshot(root, include_status_endpoint=False)
    out_dir = root / (reports_dir or DEFAULT_REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"4B436632B_H1_operator_cockpit_unified_sync_{stamp}_snapshot.json"
    out_path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"
    return f"{value}{suffix}"


def run_gui(root: Path | None = None) -> int:
    # Import tkinter lazily so CLI checks and tests work on headless environments.
    import tkinter as tk
    from tkinter import messagebox, ttk

    root_path = repo_root(root)
    app = tk.Tk()
    app.title(f"{COCKPIT_TITLE} — {CONTRACT_VERSION}")
    app.geometry("1320x840")
    app.minsize(1080, 720)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
    style.configure("SubTitle.TLabel", font=("Segoe UI", 10))
    style.configure("Card.TFrame", relief="groove", borderwidth=1, padding=10)
    style.configure("CardTitle.TLabel", font=("Segoe UI", 11, "bold"))
    style.configure("Good.TLabel", foreground="#0a7f3f", font=("Segoe UI", 10, "bold"))
    style.configure("Bad.TLabel", foreground="#b00020", font=("Segoe UI", 10, "bold"))
    style.configure("Warn.TLabel", foreground="#ad6a00", font=("Segoe UI", 10, "bold"))
    style.configure("Locked.TButton", font=("Segoe UI", 11, "bold"))

    state: dict[str, Any] = {"snapshot": build_cockpit_snapshot(root_path)}

    header = ttk.Frame(app, padding=(16, 12))
    header.pack(fill="x")
    ttk.Label(header, text=COCKPIT_TITLE, style="Title.TLabel").pack(side="left")
    status_label = ttk.Label(header, text="", style="SubTitle.TLabel")
    status_label.pack(side="right")

    notebook = ttk.Notebook(app)
    notebook.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    tab_overview = ttk.Frame(notebook, padding=12)
    tab_risk = ttk.Frame(notebook, padding=12)
    tab_shadow = ttk.Frame(notebook, padding=12)
    tab_logs = ttk.Frame(notebook, padding=12)
    tab_actions = ttk.Frame(notebook, padding=12)
    notebook.add(tab_overview, text="Overview")
    notebook.add(tab_risk, text="Risk & Evidence")
    notebook.add(tab_shadow, text="Shadow Collection")
    notebook.add(tab_logs, text="Logs")
    notebook.add(tab_actions, text="Actions")

    overview_grid = ttk.Frame(tab_overview)
    overview_grid.pack(fill="x")
    overview_cards: dict[str, ttk.Label] = {}

    def make_card(parent: ttk.Frame, row: int, col: int, title: str) -> ttk.Label:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        parent.columnconfigure(col, weight=1)
        ttk.Label(frame, text=title, style="CardTitle.TLabel").pack(anchor="w")
        value = ttk.Label(frame, text="—", wraplength=280, justify="left")
        value.pack(anchor="w", pady=(8, 0))
        return value

    for idx, key in enumerate([
        "latest_phase", "live_state", "live_lock", "second_candidate",
        "capital_caps", "emergency_stop", "shadow_state", "status_endpoint",
    ]):
        overview_cards[key] = make_card(overview_grid, idx // 4, idx % 4, key.replace("_", " ").title())

    chart_canvas = tk.Canvas(tab_overview, height=220, background="white", highlightthickness=1, highlightbackground="#d0d0d0")
    chart_canvas.pack(fill="x", pady=12)

    risk_text = tk.Text(tab_risk, height=28, wrap="word")
    risk_text.pack(fill="both", expand=True)
    risk_text.configure(state="disabled")

    shadow_text = tk.Text(tab_shadow, height=20, wrap="word")
    shadow_text.pack(fill="both", expand=True)
    shadow_text.configure(state="disabled")

    log_text = tk.Text(tab_logs, height=28, wrap="word")
    log_text.pack(fill="both", expand=True)
    log_text.configure(state="disabled")

    actions_frame = ttk.Frame(tab_actions)
    actions_frame.pack(fill="x", anchor="n")
    action_output = tk.Text(tab_actions, height=20, wrap="word")
    action_output.pack(fill="both", expand=True, pady=(12, 0))
    action_output.configure(state="disabled")

    def set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def append_action(content: str) -> None:
        action_output.configure(state="normal")
        action_output.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {content}\n")
        action_output.see("end")
        action_output.configure(state="disabled")

    def draw_chart(snapshot: CockpitSnapshot) -> None:
        chart_canvas.delete("all")
        width = max(chart_canvas.winfo_width(), 900)
        height = 220
        values = [
            ("Capital cap", snapshot.risk_caps.capital_cap_usdt or 0.0),
            ("Second max", snapshot.risk_caps.second_micro_max_notional_usdt or 0.0),
            ("Candidate", snapshot.second_micro_candidate.candidate_notional_usdt or 0.0),
            ("Daily loss", snapshot.risk_caps.daily_loss_limit_usdt or 0.0),
        ]
        max_value = max([v for _, v in values] + [1.0])
        chart_canvas.create_text(16, 16, anchor="w", text="Risk / Notional Overview (USDT)", font=("Segoe UI", 11, "bold"))
        left = 40
        top = 48
        bar_w = max(60, (width - 100) // len(values) - 24)
        scale_h = 120
        for idx, (label, value) in enumerate(values):
            x0 = left + idx * (bar_w + 28)
            bar_h = int((value / max_value) * scale_h) if max_value else 0
            y0 = top + scale_h - bar_h
            y1 = top + scale_h
            chart_canvas.create_rectangle(x0, y0, x0 + bar_w, y1, fill="#4a6fa5", outline="#344e75")
            chart_canvas.create_text(x0 + bar_w / 2, y0 - 12, text=_fmt(value), font=("Segoe UI", 9))
            chart_canvas.create_text(x0 + bar_w / 2, y1 + 18, text=label, font=("Segoe UI", 9))
        lock_text = "LIVE SUBMIT LOCKED" if snapshot.no_live_order_lock else "LIVE FLAG DETECTED"
        color = "#0a7f3f" if snapshot.no_live_order_lock else "#b00020"
        chart_canvas.create_text(width - 20, 18, anchor="e", text=lock_text, fill=color, font=("Segoe UI", 12, "bold"))

    def update_ui() -> None:
        snapshot = state["snapshot"]
        assert isinstance(snapshot, CockpitSnapshot)
        status_label.configure(text=f"{snapshot.generated_at_utc} | {snapshot.live_micro_canary_state}")
        overview_cards["latest_phase"].configure(text=snapshot.latest_accepted_phase)
        overview_cards["live_state"].configure(text=snapshot.live_micro_canary_state)
        overview_cards["live_lock"].configure(
            text="LOCKED — no 32B live submit" if snapshot.no_live_order_lock else "WARNING — live flag detected",
            style="Good.TLabel" if snapshot.no_live_order_lock else "Bad.TLabel",
        )
        overview_cards["second_candidate"].configure(
            text=f"{snapshot.second_micro_candidate.symbol} {snapshot.second_micro_candidate.side} {_fmt(snapshot.second_micro_candidate.candidate_qty)} ETH / {_fmt(snapshot.second_micro_candidate.candidate_notional_usdt)} USDT"
        )
        overview_cards["capital_caps"].configure(
            text=f"capital={_fmt(snapshot.risk_caps.capital_cap_usdt)} | second={_fmt(snapshot.risk_caps.second_micro_max_notional_usdt)} | daily loss={_fmt(snapshot.risk_caps.daily_loss_limit_usdt)}"
        )
        overview_cards["emergency_stop"].configure(
            text="ARMED" if snapshot.emergency_stop_armed else "NOT VERIFIED",
            style="Good.TLabel" if snapshot.emergency_stop_armed else "Warn.TLabel",
        )
        overview_cards["shadow_state"].configure(
            text="ACTIVE / clean" if snapshot.shadow_health.active else "Needs review",
            style="Good.TLabel" if snapshot.shadow_health.active else "Warn.TLabel",
        )
        overview_cards["status_endpoint"].configure(
            text="online" if snapshot.status_endpoint_online else "offline / file evidence mode",
            style="Good.TLabel" if snapshot.status_endpoint_online else "Warn.TLabel",
        )
        draw_chart(snapshot)
        risk_payload = {
            "operator_message": snapshot.operator_message,
            "phase_31b": asdict(snapshot.phase_31b),
            "phase_32a": asdict(snapshot.phase_32a),
            "phase_32b": asdict(snapshot.phase_32b),
            "risk_caps": asdict(snapshot.risk_caps),
            "second_micro_candidate": asdict(snapshot.second_micro_candidate),
            "approved_for_live_real_order": snapshot.approved_for_live_real_order,
            "approved_for_second_micro_order": snapshot.approved_for_second_micro_order,
            "no_live_order_lock": snapshot.no_live_order_lock,
        }
        set_text(risk_text, json.dumps(risk_payload, ensure_ascii=False, indent=2))
        shadow_payload = asdict(snapshot.shadow_health)
        shadow_payload["log_tail"] = "<see Logs tab>"
        set_text(shadow_text, json.dumps(shadow_payload, ensure_ascii=False, indent=2))
        set_text(log_text, snapshot.shadow_health.log_tail or "No shadow scheduler log found yet.")

    def refresh() -> None:
        state["snapshot"] = build_cockpit_snapshot(root_path)
        update_ui()
        append_action("Snapshot refreshed.")

    def write_snapshot_action() -> None:
        path = write_snapshot_report(root_path)
        append_action(f"Cockpit snapshot written: {path}")

    def open_reports() -> None:
        path = root_path / DEFAULT_REPORTS_DIR
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer", str(path)])  # noqa: S603,S607 - operator local action.
        else:
            append_action(str(path))

    def start_shadow_task() -> None:
        if os.name != "nt":
            append_action("Scheduled task action is Windows-only.")
            return
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Start-ScheduledTask -TaskName TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection; Start-Sleep -Seconds 3; Get-ScheduledTaskInfo -TaskName TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection | Format-List LastRunTime,LastTaskResult,NextRunTime,NumberOfMissedRuns,TaskName",
        ]
        def worker() -> None:
            proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=root_path, check=False, timeout=120)
            app.after(0, lambda: append_action(proc.stdout.strip() or f"Scheduled task returncode={proc.returncode}"))
            app.after(0, refresh)
        threading.Thread(target=worker, daemon=True).start()
        append_action("Shadow scheduled task start requested.")

    def show_locked() -> None:
        messagebox.showwarning(
            "Live submit locked",
            "32B-H1 Operator Cockpit does not submit live orders. 32C explicit phase is required for any exchange submit.",
        )

    ttk.Button(actions_frame, text="Refresh", command=refresh).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
    ttk.Button(actions_frame, text="Write cockpit snapshot", command=write_snapshot_action).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
    ttk.Button(actions_frame, text="Open production_hardening", command=open_reports).grid(row=0, column=2, padx=6, pady=6, sticky="ew")
    ttk.Button(actions_frame, text="Start no-order shadow task", command=start_shadow_task).grid(row=0, column=3, padx=6, pady=6, sticky="ew")
    ttk.Button(actions_frame, text="LIVE SUBMIT LOCKED", command=show_locked, style="Locked.TButton").grid(row=0, column=4, padx=6, pady=6, sticky="ew")
    for i in range(5):
        actions_frame.columnconfigure(i, weight=1)

    update_ui()
    app.after(30000, refresh)
    app.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    if "--snapshot-json" in argv:
        snapshot = build_cockpit_snapshot(root, include_status_endpoint="--no-status-endpoint" not in argv)
        print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if "--write-snapshot" in argv:
        path = write_snapshot_report(root)
        print(path)
        return 0
    return run_gui(root)


if __name__ == "__main__":
    raise SystemExit(main())
