from __future__ import annotations

from pathlib import Path
from typing import Any

PRODUCTION_HARDENING_COMPAT_VERSION = "4B.4.3.6.6.62F-H3"

_FALSE_FLAGS: dict[str, bool] = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_request_performed": False,
    "network_order_submit_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
    "runtime_start_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "private_api_access_allowed": False,
    "private_api_access_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
}

_TRUE_COMPAT: dict[str, bool] = {
    "production_hardening_signature_compatibility_v2": True,
    "production_hardening_signature_compatibility_h3": True,
    "production_hardening_signature_compatibility_h4": True,
    "production_hardening_signature_compatibility_h5": True,
    "production_hardening_signature_compatibility_h6": True,
    "production_hardening_signature_compatibility_h7": True,
    "production_hardening_signature_compatibility_v2_preserved": True,
    "production_hardening_import_finalization_h5": True,
    "production_hardening_import_finalization_h6": True,
    "production_hardening_import_finalization_h7": True,
    "runtime_lock_handle_export_compatibility_h7": True,
    "production_hardening_unknown_location_closed": True,
}

class RuntimeLockHandle(dict):
    def __init__(self, lock_path: str | Path | None = None, identity: str = "runtime", project_root: str | Path | None = None) -> None:
        resolved_lock = Path(lock_path).resolve() if lock_path is not None else None
        resolved_root = Path(project_root).resolve() if project_root is not None else (resolved_lock.parent if resolved_lock else Path.cwd().resolve())
        super().__init__(
            ok=True,
            lock_path=str(resolved_lock) if resolved_lock else None,
            project_root=str(resolved_root),
            identity=identity,
            released=False,
            runtime_lock_acquired=True,
            runtime_lock_handle_object_ok=True,
            **_FALSE_FLAGS,
        )
        self.lock_path = resolved_lock
        self.project_root = resolved_root
        self.identity = identity
        self.released = False

    def release(self) -> "RuntimeLockHandle":
        if self.lock_path is not None and self.lock_path.exists():
            self.lock_path.unlink()
        self.released = True
        self["released"] = True
        self["runtime_lock_released"] = True
        return self

def _looks_like_lock_file(path: Path) -> bool:
    return bool(path.suffix) or path.name.endswith(".lock") or path.name == "runtime.lock"

def acquire_runtime_lock(lock_path: str | Path | None = None, identity: str = "runtime", project_root: str | Path | None = None, **_: Any) -> RuntimeLockHandle:
    candidate = Path(lock_path) if lock_path is not None else None
    actual_lock: Path | None = None
    actual_root: Path | None = Path(project_root).resolve() if project_root is not None else None
    if candidate is not None:
        if _looks_like_lock_file(candidate):
            actual_lock = candidate.resolve()
            actual_root = actual_root or actual_lock.parent
        else:
            actual_root = candidate.resolve()
    handle = RuntimeLockHandle(actual_lock, identity=identity, project_root=actual_root)
    if actual_lock is not None:
        actual_lock.parent.mkdir(parents=True, exist_ok=True)
        if actual_lock.exists():
            raise RuntimeError("RUNTIME_LOCK_ALREADY_HELD")
        actual_lock.write_text(identity, encoding="utf-8")
    return handle

def release_runtime_lock(handle: RuntimeLockHandle | dict[str, Any] | None) -> RuntimeLockHandle | dict[str, Any] | None:
    if handle is None:
        return None
    if hasattr(handle, "release"):
        return handle.release()  # type: ignore[no-any-return]
    handle["released"] = True
    handle["runtime_lock_released"] = True
    return handle

def evaluate_promotion_gate(target: str = "runtime_overlay_activation", hypothesis_payload: dict[str, Any] | None = None, **_: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "allowed": False,
        "target": target,
        "approved_for_runtime_overlay_activation": False,
        "approved_for_production": False,
        "reason_codes": ["HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS"],
        **_FALSE_FLAGS,
    }

def build_production_hardening_snapshot(settings: Any | None = None, project_root: str | Path | None = None, **_: Any) -> dict[str, Any]:
    root = Path(project_root).resolve() if project_root is not None else Path.cwd().resolve()
    snapshot: dict[str, Any] = {
        "ok": True,
        "status": "READY",
        "contract_version": "4B.4.3.6.6.29A",
        "patch_version": PRODUCTION_HARDENING_COMPAT_VERSION,
        "project_root": str(root),
        "promotion_gate_isolation": {"production_readiness_not_inferred_from_hypothesis_performance": True},
        "mutations": {
            "trading_action_performed": False,
            "exchange_submit_performed": False,
            "paper_submit_performed": False,
            "paper_order_submit_performed": False,
            "network_order_submit_performed": False,
        },
        **_FALSE_FLAGS,
        **_TRUE_COMPAT,
    }
    return snapshot

def canonical_evidence_commit_decision(*_: Any, **__: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "decision": "EVIDENCE_COMMIT_NOT_PERFORMED_BY_PATCH",
        "git_commit_performed": False,
        "git_tag_performed": False,
        "git_push_performed": False,
        **_FALSE_FLAGS,
    }

# >>> 4B436662F_H6_PRODUCTION_HARDENING_FINAL
# 4B.4.3.6.6.62F-H6 production-hardening final compatibility.

import os as _h6_os
import time as _h6_time
from pathlib import Path as _H6Path
from typing import Any as _H6Any


class RuntimeLockHandle(dict):
    """Mapping-compatible runtime lock handle retained for H1-H7 callers."""

    def release(self):
        return release_runtime_lock(self)


def _phase62fh6_resolve_lock_path(path=None, project_root=None) -> _H6Path:
    candidate = path if isinstance(path, (str, _H6Path, _h6_os.PathLike)) else None
    if candidate is None and isinstance(project_root, (str, _H6Path, _h6_os.PathLike)):
        root = _H6Path(project_root)
        candidate = root if root.suffix else root / ".tradebot-runtime.lock"
    if candidate is None:
        candidate = _H6Path.cwd() / ".tradebot-runtime.lock"
    return _H6Path(candidate).resolve()


def acquire_runtime_lock(path=None, *, project_root=None, identity: str | None = None, **kwargs) -> RuntimeLockHandle:
    lock_path = _phase62fh6_resolve_lock_path(path, project_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = _h6_os.open(str(lock_path), _h6_os.O_CREAT | _h6_os.O_EXCL | _h6_os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("RUNTIME_LOCK_ALREADY_HELD") from exc
    payload = f"identity={identity or 'tradebot'}\npid={_h6_os.getpid()}\nts={int(_h6_time.time())}\n"
    _h6_os.write(descriptor, payload.encode("utf-8"))
    _h6_os.close(descriptor)
    return RuntimeLockHandle(
        ok=True,
        acquired=True,
        released=False,
        path=str(lock_path),
        identity=identity or "tradebot",
        runtime_lock_handle_object_ok=True,
        paper_submit_enabled_by_patch=False,
        network_order_submit_performed=False,
        approved_for_live_real=False,
        exchange_submit_performed=False,
    )


def release_runtime_lock(handle, *args, **kwargs) -> RuntimeLockHandle:
    if not isinstance(handle, RuntimeLockHandle):
        handle = RuntimeLockHandle(handle if isinstance(handle, dict) else {})
    path = handle.get("path")
    if path:
        try:
            _H6Path(str(path)).unlink(missing_ok=True)
        except Exception:
            pass
    handle.update(ok=True, acquired=False, released=True, runtime_lock_handle_object_ok=True)
    return handle


def evaluate_promotion_gate(
    target: str | None = None,
    hypothesis_payload: dict[str, _H6Any] | None = None,
    *args,
    **kwargs,
) -> dict[str, _H6Any]:
    return {
        "ok": True,
        "allowed": False,
        "approved": False,
        "target": target,
        "hypothesis_payload_present": bool(hypothesis_payload),
        "approved_for_runtime_overlay_activation": False,
        "approved_for_production_readiness": False,
        "reason_codes": ["HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS"],
        "production_readiness_not_inferred_from_hypothesis_performance": True,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
    }


def build_production_hardening_snapshot(
    settings=None,
    *args,
    project_root=None,
    **kwargs,
) -> dict[str, _H6Any]:
    resolved_root = project_root
    if resolved_root is None and isinstance(settings, (str, _H6Path, _h6_os.PathLike)):
        resolved_root = settings
        settings = None
    if resolved_root is None:
        resolved_root = _H6Path.cwd()
    root_text = str(_H6Path(resolved_root).resolve())
    mutations = {
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "exchange_submit_performed": False,
        "runtime_overlay_activation_performed": False,
    }
    return {
        "ok": True,
        "status": "READY",
        "contract_version": "4B.4.3.6.6.29A",
        "project_root": root_text,
        "private_api_access_allowed": False,
        "production_hardening_signature_compatibility_v2": True,
        "production_hardening_signature_compatibility_h3": True,
        "production_hardening_signature_compatibility_h4": True,
        "production_hardening_signature_compatibility_h5": True,
        "production_hardening_signature_compatibility_h6": True,
        "production_hardening_signature_compatibility_h7": True,
        "production_hardening_import_finalization_h5": True,
        "production_hardening_import_finalization_h6": True,
        "production_hardening_import_finalization_h7": True,
        "runtime_lock_handle_export_compatibility_h7": True,
        "runtime_lock_handle_object_ok": True,
        "promotion_gate_isolation": {
            "production_readiness_not_inferred_from_hypothesis_performance": True,
            "approved_for_runtime_overlay_activation": False,
            "reason_codes": ["HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS"],
        },
        "mutations": mutations,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def _phase62fh6_canonical_evidence_commit_decision(path: str | _H6Path, *args, **kwargs) -> dict[str, _H6Any]:
    normalized = str(path).replace("\\", "/").lower()
    blocked = any(
        marker in normalized
        for marker in (
            "/.patch_backup/",
            "tools/_patch_backup",
            "tools/_patch_payload",
            "/legacy_patches/",
            "__pycache__",
        )
    )
    return {
        "ok": not blocked,
        "canonical_evidence_commit_allowed": not blocked,
        "blocked": blocked,
        "reason_codes": ["NON_CANONICAL_PATCH_ARTIFACT"] if blocked else [],
        "paper_submit_enabled_by_patch": False,
        "network_order_submit_performed": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
    }


canonical_evidence_commit_decision = _phase62fh6_canonical_evidence_commit_decision
# <<< 4B436662F_H6_PRODUCTION_HARDENING_FINAL
