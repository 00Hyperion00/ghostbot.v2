import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PHASE = "4B.4.3.6.6.21b"
MIN_CONTRACT_VERSION = "4B.4.3.6.6.20"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass
class SmokeResult:
    name: str
    ok: bool
    url: str
    status_code: int | None = None
    elapsed_sec: float = 0.0
    reason: str | None = None
    details: dict[str, Any] | None = None


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _version_parts(value: str) -> list[int]:
    parts: list[int] = []
    for token in str(value or "").replace("-", ".").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return parts


def contract_version_at_least(actual: str | None, minimum: str = MIN_CONTRACT_VERSION) -> bool:
    if not actual:
        return False
    left = _version_parts(actual)
    right = _version_parts(minimum)
    max_len = max(len(left), len(right))
    left.extend([0] * (max_len - len(left)))
    right.extend([0] * (max_len - len(right)))
    return left >= right


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 5.0,
) -> tuple[int, Any, float]:
    url = _join_url(base_url, path)
    data: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout_sec) as response:  # noqa: S310 - local operator smoke tool
        raw = response.read().decode("utf-8", errors="replace")
        elapsed = time.perf_counter() - started
        if not raw.strip():
            parsed: Any = None
        else:
            parsed = json.loads(raw)
        return int(response.status), parsed, elapsed


def evaluate_health(payload: Any) -> tuple[bool, str | None, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "health payload is not a JSON object", {}
    ok = bool(payload.get("ok"))
    details = {
        "ok": payload.get("ok"),
        "running": payload.get("running"),
        "symbol": payload.get("symbol"),
        "bootstrap_ok": payload.get("bootstrap_ok"),
        "bootstrap_error": payload.get("bootstrap_error"),
    }
    if not ok:
        return False, "health.ok is not True", details
    return True, None, details


def evaluate_status(payload: Any, *, minimum_contract: str = MIN_CONTRACT_VERSION) -> tuple[bool, str | None, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "status payload is not a JSON object", {}
    contract_version = str(payload.get("contract_version") or "")
    required_snapshots = [
        "ai_snapshot",
        "risk_snapshot",
        "position_snapshot",
        "pending_snapshot",
        "config_safety_snapshot",
        "performance_snapshot",
        "model_quality_snapshot",
    ]
    missing = [name for name in required_snapshots if name not in payload]
    details = {
        "contract_version": contract_version,
        "state": payload.get("state"),
        "symbol": payload.get("symbol"),
        "missing_snapshots": missing,
        "config_severity": (payload.get("config_safety_snapshot") or {}).get("severity") if isinstance(payload.get("config_safety_snapshot"), dict) else None,
    }
    if not contract_version_at_least(contract_version, minimum_contract):
        return False, f"contract_version {contract_version!r} is below {minimum_contract}", details
    if missing:
        return False, "status payload missing required snapshots: " + ", ".join(missing), details
    return True, None, details


def evaluate_collection_payload(payload: Any, *, label: str) -> tuple[bool, str | None, dict[str, Any]]:
    if isinstance(payload, list):
        return True, None, {"shape": "list", "count": len(payload)}
    if isinstance(payload, dict):
        candidates = ["events", "items", "logs", "results", "entries"]
        count = None
        for key in candidates:
            value = payload.get(key)
            if isinstance(value, list):
                count = len(value)
                break
        return True, None, {"shape": "dict", "count": count, "keys": sorted(str(k) for k in payload.keys())[:20]}
    return False, f"{label} payload is neither object nor list", {}


def run_endpoint(
    base_url: str,
    name: str,
    path: str,
    evaluator,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 5.0,
) -> SmokeResult:
    url = _join_url(base_url, path)
    try:
        status_code, parsed, elapsed = request_json(base_url, path, method=method, payload=payload, timeout_sec=timeout_sec)
        ok, reason, details = evaluator(parsed)
        return SmokeResult(name=name, ok=ok, url=url, status_code=status_code, elapsed_sec=elapsed, reason=reason, details=details)
    except urllib.error.HTTPError as exc:
        code = int(getattr(exc, "code", 0) or 0)
        if name == "diagnostics" and code == 404:
            return SmokeResult(
                name=name,
                ok=True,
                url=url,
                status_code=404,
                elapsed_sec=0.0,
                reason="optional endpoint not available (404)",
                details={"optional": True, "fallback": "status snapshots"},
            )
        return SmokeResult(
            name=name,
            ok=False,
            url=url,
            status_code=code or None,
            elapsed_sec=0.0,
            reason=f"request failed: {exc}",
            details={"exception_type": type(exc).__name__},
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return SmokeResult(name=name, ok=False, url=url, elapsed_sec=0.0, reason=f"request failed: {exc}", details={"exception_type": type(exc).__name__})


def build_smoke_plan(include_logs: bool = True) -> list[tuple[str, str, Any]]:
    plan: list[tuple[str, str, Any]] = [
        ("health", "/health", evaluate_health),
        ("status", "/status", evaluate_status),
        ("events_audit", "/events/audit?limit=5", lambda payload: evaluate_collection_payload(payload, label="events_audit")),
        ("diagnostics", "/diagnostics", lambda payload: (isinstance(payload, dict), None if isinstance(payload, dict) else "diagnostics payload is not an object", {"keys": sorted(payload.keys())[:20]} if isinstance(payload, dict) else {})),
    ]
    if include_logs:
        plan.append(("logs", "/logs?limit=20", lambda payload: evaluate_collection_payload(payload, label="logs")))
    return plan


def write_reports(root: Path, results: list[SmokeResult], *, stamp: str, base_url: str) -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436621_runtime_smoke_{stamp}.json"
    md_path = reports_dir / f"4B436621_runtime_smoke_{stamp}.md"
    payload = {
        "phase": PHASE,
        "base_url": base_url,
        "generated_at": stamp,
        "ok": all(item.ok for item in results),
        "results": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        f"# {PHASE} Runtime Smoke Report",
        "",
        f"- Base URL: `{base_url}`",
        f"- Result: **{'PASS' if payload['ok'] else 'FAIL'}**",
        "",
        "| Check | Result | Status | Reason |",
        "|---|---:|---:|---|",
    ]
    for item in results:
        lines.append(f"| {item.name} | {'PASS' if item.ok else 'FAIL'} | {item.status_code or '-'} | {item.reason or '-'} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run_smoke(base_url: str, *, timeout_sec: float, include_logs: bool, root: Path) -> tuple[bool, list[SmokeResult], Path, Path]:
    results = [run_endpoint(base_url, name, path, evaluator, timeout_sec=timeout_sec) for name, path, evaluator in build_smoke_plan(include_logs=include_logs)]
    json_path, md_path = write_reports(root, results, stamp=_now_stamp(), base_url=base_url)
    return all(item.ok for item in results), results, json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{PHASE} runtime API smoke gate")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--root", default=".")
    parser.add_argument("--timeout-sec", type=float, default=5.0)
    parser.add_argument("--skip-logs", action="store_true", help="Skip /logs smoke check")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    ok, results, json_path, md_path = run_smoke(args.base_url, timeout_sec=args.timeout_sec, include_logs=not args.skip_logs, root=root)
    print(f"{PHASE} runtime smoke {'PASSED' if ok else 'FAILED'}")
    for item in results:
        print(f" - {item.name}: {'PASS' if item.ok else 'FAIL'} ({item.reason or 'OK'})")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
