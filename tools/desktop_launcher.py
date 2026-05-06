from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8000
DEFAULT_CONFIG = 'config.local.yaml'
LAUNCHER_CONTRACT_VERSION = '4B.4.3.6.6.16'


@dataclass(slots=True)
class LauncherPaths:
    project_root: str
    src_path: str
    config_path: str
    logs_dir: str
    python_executable: str


@dataclass(slots=True)
class LauncherCheck:
    contract_version: str
    ok: bool
    project_root: str
    config_exists: bool
    src_exists: bool
    python_executable: str
    python_ok: bool
    dependencies_ok: bool
    missing_dependencies: list[str]
    port_open: bool
    api_online: bool
    api_health: dict[str, Any] | None
    warnings: list[str]
    errors: list[str]


def project_root_from_file(file_path: str | Path | None = None) -> Path:
    if file_path is None:
        file_path = __file__
    return Path(file_path).resolve().parents[1]


def resolve_paths(project_root: Path, config: str | Path = DEFAULT_CONFIG) -> LauncherPaths:
    config_path = Path(config)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    return LauncherPaths(
        project_root=str(project_root),
        src_path=str(project_root / 'src'),
        config_path=str(config_path),
        logs_dir=str(project_root / 'logs'),
        python_executable=sys.executable,
    )


def build_pythonpath(project_root: Path, existing: str | None = None) -> str:
    src = str(project_root / 'src')
    if not existing:
        return src
    parts = [p for p in existing.split(os.pathsep) if p]
    if src not in parts:
        parts.insert(0, src)
    return os.pathsep.join(parts)


def launcher_env(project_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env['PYTHONPATH'] = build_pythonpath(project_root, env.get('PYTHONPATH'))
    env['PYTHONUNBUFFERED'] = '1'
    return env


def build_api_command(config_path: str | Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> list[str]:
    return [
        sys.executable,
        '-m',
        'tradebot.cli',
        'api',
        '--config',
        str(config_path),
        '--host',
        host,
        '--port',
        str(int(port)),
    ]


def build_dashboard_command(config_path: str | Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> list[str]:
    return [
        sys.executable,
        '-m',
        'tradebot.cli',
        'dashboard',
        '--config',
        str(config_path),
        '--host',
        host,
        '--port',
        str(int(port)),
    ]


def port_is_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def fetch_health(host: str, port: int, timeout: float = 1.0) -> dict[str, Any] | None:
    url = f'http://{host}:{int(port)}/health'
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = resp.read().decode('utf-8')
        data = json.loads(payload)
        return data if isinstance(data, dict) else None
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def check_dependencies(required_modules: Iterable[str] = ('yaml', 'fastapi', 'uvicorn', 'requests', 'httpx')) -> list[str]:
    missing: list[str] = []
    for module_name in required_modules:
        try:
            __import__(module_name)
        except Exception:
            missing.append(module_name)
    return missing


def run_check(project_root: Path, config: str | Path, host: str, port: int) -> LauncherCheck:
    paths = resolve_paths(project_root, config)
    warnings: list[str] = []
    errors: list[str] = []
    config_exists = Path(paths.config_path).exists()
    src_exists = Path(paths.src_path).exists()
    if not config_exists:
        errors.append(f'CONFIG_NOT_FOUND:{paths.config_path}')
    if not src_exists:
        errors.append(f'SRC_NOT_FOUND:{paths.src_path}')
    missing = check_dependencies()
    if missing:
        errors.append('MISSING_DEPENDENCIES:' + ','.join(missing))
    health = fetch_health(host, port, timeout=0.8)
    online = bool(health and health.get('ok') is True)
    open_port = port_is_open(host, port)
    if open_port and not online:
        warnings.append('PORT_OPEN_BUT_HEALTH_NOT_OK')
    return LauncherCheck(
        contract_version=LAUNCHER_CONTRACT_VERSION,
        ok=bool(config_exists and src_exists and not missing),
        project_root=str(project_root),
        config_exists=config_exists,
        src_exists=src_exists,
        python_executable=sys.executable,
        python_ok=True,
        dependencies_ok=not missing,
        missing_dependencies=missing,
        port_open=open_port,
        api_online=online,
        api_health=health,
        warnings=warnings,
        errors=errors,
    )


def wait_for_health(host: str, port: int, timeout_sec: float = 20.0, poll_sec: float = 0.5) -> dict[str, Any] | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        health = fetch_health(host, port, timeout=1.0)
        if health and health.get('ok') is True:
            return health
        time.sleep(poll_sec)
    return None


def creationflags_for_new_console() -> int:
    if os.name != 'nt':
        return 0
    return getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)


def start_api_process(project_root: Path, config_path: Path, host: str, port: int) -> subprocess.Popen[str]:
    log_dir = project_root / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / 'launcher_api.log'
    cmd = build_api_command(config_path, host, port)
    env = launcher_env(project_root)
    if os.name == 'nt':
        return subprocess.Popen(cmd, cwd=str(project_root), env=env, creationflags=creationflags_for_new_console())
    log_file = log_path.open('a', encoding='utf-8')
    return subprocess.Popen(cmd, cwd=str(project_root), env=env, stdout=log_file, stderr=subprocess.STDOUT, text=True)


def run_dashboard(project_root: Path, config_path: Path, host: str, port: int) -> int:
    cmd = build_dashboard_command(config_path, host, port)
    env = launcher_env(project_root)
    return subprocess.call(cmd, cwd=str(project_root), env=env)


def print_check(check: LauncherCheck) -> None:
    print(json.dumps(asdict(check), ensure_ascii=False, indent=2))


def ensure_or_raise(check: LauncherCheck) -> None:
    if not check.ok:
        print_check(check)
        raise SystemExit(2)


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve() if args.project_root else project_root_from_file()
    check = run_check(root, args.config, args.host, args.port)
    print_check(check)
    return 0 if check.ok else 2


def cmd_api(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve() if args.project_root else project_root_from_file()
    paths = resolve_paths(root, args.config)
    check = run_check(root, args.config, args.host, args.port)
    ensure_or_raise(check)
    if check.api_online:
        print(f'API already online: http://{args.host}:{args.port}/health')
        return 0
    proc = start_api_process(root, Path(paths.config_path), args.host, args.port)
    health = wait_for_health(args.host, args.port, timeout_sec=args.timeout)
    if health:
        print(f'API started pid={proc.pid} health_ok=True')
        return 0
    print(f'API start submitted pid={proc.pid}, but health check did not become OK within {args.timeout:.0f}s')
    return 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve() if args.project_root else project_root_from_file()
    paths = resolve_paths(root, args.config)
    check = run_check(root, args.config, args.host, args.port)
    ensure_or_raise(check)
    return run_dashboard(root, Path(paths.config_path), args.host, args.port)


def cmd_one_click(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve() if args.project_root else project_root_from_file()
    paths = resolve_paths(root, args.config)
    check = run_check(root, args.config, args.host, args.port)
    ensure_or_raise(check)
    if check.api_online:
        print('API already online; attaching dashboard.')
    else:
        proc = start_api_process(root, Path(paths.config_path), args.host, args.port)
        health = wait_for_health(args.host, args.port, timeout_sec=args.timeout)
        if not health:
            print(f'API start submitted pid={proc.pid}, but health check did not become OK. Dashboard will still open and show offline fallback if needed.')
        else:
            print(f'API started pid={proc.pid}')
    return run_dashboard(root, Path(paths.config_path), args.host, args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='TradeBot desktop launcher helper')
    parser.add_argument('--project-root', default=None)
    parser.add_argument('--config', default=DEFAULT_CONFIG)
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    api = sub.add_parser('api')
    api.add_argument('--timeout', type=float, default=20.0)
    sub.add_parser('dashboard')
    one = sub.add_parser('one-click')
    one.add_argument('--timeout', type=float, default=20.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'check':
        return cmd_check(args)
    if args.command == 'api':
        return cmd_api(args)
    if args.command == 'dashboard':
        return cmd_dashboard(args)
    if args.command == 'one-click':
        return cmd_one_click(args)
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
